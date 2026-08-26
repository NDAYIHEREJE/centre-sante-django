// ==========================================================
// Configuration
// ==========================================================
const API_BASE = "";  // chemins relatifs : frontend et API servis par le même serveur Django

let session = {
  token: localStorage.getItem("token") || null,
  role: localStorage.getItem("role") || null,
};

// ==========================================================
// Aide — appel API générique
// ==========================================================
async function api(path, { method = "GET", body = null, form = false } = {}) {
  const headers = {};
  if (session.token) headers["Authorization"] = "Bearer " + session.token;

  let payload = body;
  if (body && !form) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(API_BASE + path, { method, headers, body: payload });
  if (!res.ok) {
    let detail = "Erreur inconnue";
    try { detail = (await res.json()).detail; } catch (e) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ==========================================================
// Navigation entre vues
// ==========================================================
function afficherVue(role) {
  document.querySelectorAll(".view").forEach(v => v.classList.add("hidden"));
  document.getElementById("user-info").classList.toggle("hidden", !role);

  if (!role) {
    document.getElementById("view-auth").classList.remove("hidden");
    return;
  }
  if (role === "PATIENT") {
    document.getElementById("view-patient").classList.remove("hidden");
    chargerAnnuaireMedecins();
    chargerMesRendezVous();
    chargerMesPrescriptions();
  } else if (role === "MEDECIN") {
    document.getElementById("view-medecin").classList.remove("hidden");
    chargerRdvMedecin("CONFIRME");
    chargerMesDisponibilites();
  } else if (role === "ADMINISTRATEUR") {
    document.getElementById("view-admin").classList.remove("hidden");
    chargerTableauDeBord();
    chargerUtilisateurs();
    chargerRdvAdmin("");
    chargerMedicamentsAdmin();
  } else {
    document.getElementById("view-staff").classList.remove("hidden");
    chargerRdvStaff("EN_ATTENTE");
  }
}

function majEnteteUtilisateur() {
  document.getElementById("user-label").textContent =
    session.role === "PATIENT" ? "Espace patient"
    : session.role === "MEDECIN" ? "Espace médecin"
    : session.role === "ADMINISTRATEUR" ? "Espace administrateur"
    : "Espace réceptionniste";
}

// ==========================================================
// Authentification
// ==========================================================
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    const cible = tab.dataset.tab;
    document.getElementById("form-login").classList.toggle("hidden", cible !== "login");
    document.getElementById("form-register").classList.toggle("hidden", cible !== "register");
  });
});

document.getElementById("form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  const erreurEl = document.getElementById("login-error");
  erreurEl.textContent = "";
  try {
    const form = new URLSearchParams();
    form.set("username", document.getElementById("login-email").value);
    form.set("password", document.getElementById("login-password").value);

    const res = await fetch(API_BASE + "/auth/connexion", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Connexion refusée");
    const data = await res.json();

    session = { token: data.access_token, role: data.role };
    localStorage.setItem("token", session.token);
    localStorage.setItem("role", session.role);

    majEnteteUtilisateur();
    afficherVue(session.role);
  } catch (err) {
    erreurEl.textContent = err.message;
  }
});

document.getElementById("form-register").addEventListener("submit", async (e) => {
  e.preventDefault();
  const erreurEl = document.getElementById("register-error");
  erreurEl.textContent = "";
  try {
    await api("/auth/inscription-patient", {
      method: "POST",
      body: {
        email: document.getElementById("reg-email").value,
        mot_de_passe: document.getElementById("reg-password").value,
        nom: document.getElementById("reg-nom").value,
        prenom: document.getElementById("reg-prenom").value,
        date_naissance: document.getElementById("reg-naissance").value || null,
      },
    });
    // Bascule automatique vers l'onglet connexion après inscription réussie.
    document.querySelector('.tab[data-tab="login"]').click();
    document.getElementById("login-email").value = document.getElementById("reg-email").value;
  } catch (err) {
    erreurEl.textContent = err.message;
  }
});

document.getElementById("btn-logout").addEventListener("click", () => {
  session = { token: null, role: null };
  localStorage.removeItem("token");
  localStorage.removeItem("role");
  afficherVue(null);
});

// ==========================================================
// Espace patient — prise de rendez-vous
// ==========================================================
async function chargerAnnuaireMedecins() {
  const select = document.getElementById("rdv-medecin");
  try {
    const medecins = await api("/medecins");
    select.innerHTML = medecins
      .map(m => `<option value="${m.id}">Dr ${m.prenom} ${m.nom} — ${m.specialite}</option>`)
      .join("");
  } catch (err) {
    select.innerHTML = `<option>Impossible de charger les médecins</option>`;
  }
}

document.getElementById("btn-charger-creneaux").addEventListener("click", async () => {
  const medecinId = document.getElementById("rdv-medecin").value;
  const jour = document.getElementById("rdv-date").value;
  const conteneur = document.getElementById("creneaux-libres");
  const message = document.getElementById("rdv-message");
  message.textContent = "";
  conteneur.innerHTML = "";

  if (!medecinId || !jour) {
    message.textContent = "Choisissez un médecin et une date.";
    return;
  }
  try {
    const creneaux = await api(`/medecins/${medecinId}/disponibilites?jour=${jour}`);
    if (creneaux.length === 0) {
      conteneur.innerHTML = `<span class="empty">Aucun créneau disponible ce jour-là.</span>`;
      return;
    }
    creneaux.forEach(c => {
      const heure = new Date(c.date_heure).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
      const chip = document.createElement("button");
      chip.className = "chip";
      chip.textContent = heure;
      chip.addEventListener("click", () => demanderRdv(medecinId, c.date_heure));
      conteneur.appendChild(chip);
    });
  } catch (err) {
    message.textContent = err.message;
  }
});

async function demanderRdv(medecinId, dateHeure) {
  const message = document.getElementById("rdv-message");
  try {
    await api("/rendezvous", {
      method: "POST",
      body: { medecin_id: Number(medecinId), date_heure: dateHeure },
    });
    message.textContent = "Demande envoyée. Statut : en attente de confirmation.";
    chargerMesRendezVous();
  } catch (err) {
    message.textContent = err.message; // ex. créneau déjà pris (409)
  }
}

async function chargerMesRendezVous() {
  const conteneur = document.getElementById("liste-mes-rdv");
  conteneur.innerHTML = "";
  const rdvs = await api("/rendezvous");
  if (rdvs.length === 0) {
    conteneur.innerHTML = `<span class="empty">Aucun rendez-vous pour le moment.</span>`;
    return;
  }
  rdvs.forEach(r => conteneur.appendChild(carteRdv(r, false)));
}

async function chargerMesPrescriptions() {
  const conteneur = document.getElementById("liste-mes-prescriptions");
  conteneur.innerHTML = "";
  const prescriptions = await api("/patients/moi/prescriptions");
  if (prescriptions.length === 0) {
    conteneur.innerHTML = `<span class="empty">Aucune prescription enregistrée.</span>`;
    return;
  }
  prescriptions.forEach(p => {
    const item = document.createElement("div");
    item.className = "list-item";
    const date = new Date(p.date_prescription).toLocaleDateString("fr-FR");
    const meds = p.lignes.map(l => `Médicament #${l.medicament_id} — ${l.posologie}`).join(", ");
    item.innerHTML = `<div><div>${meds}</div><div class="meta">Prescrit le ${date}</div></div>`;
    conteneur.appendChild(item);
  });
}

// ==========================================================
// Espace médecin / réceptionniste — validation des RDV
// ==========================================================
document.querySelectorAll(".chip-filter").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".chip-filter").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    chargerRdvStaff(btn.dataset.statut);
  });
});

async function chargerRdvStaff(statut) {
  const conteneur = document.getElementById("liste-rdv-staff");
  conteneur.innerHTML = "";
  const query = statut ? `?statut=${statut}` : "";
  const rdvs = await api("/rendezvous" + query);
  if (rdvs.length === 0) {
    conteneur.innerHTML = `<span class="empty">Aucun rendez-vous dans cette catégorie.</span>`;
    return;
  }
  rdvs.forEach(r => conteneur.appendChild(carteRdv(r, true)));
}

function carteRdv(r, avecActions) {
  const item = document.createElement("div");
  item.className = "list-item";
  const date = new Date(r.date_heure).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });

  let actionsHtml = "";
  if (avecActions && r.statut === "EN_ATTENTE") {
    actionsHtml = `
      <div class="actions">
        <button class="btn-mini confirm" data-id="${r.id}" data-statut="CONFIRME">Confirmer</button>
        <button class="btn-mini cancel" data-id="${r.id}" data-statut="ANNULE">Annuler</button>
      </div>`;
  } else if (avecActions && r.statut === "CONFIRME") {
    actionsHtml = `
      <div class="actions">
        <button class="btn-mini cancel" data-id="${r.id}" data-statut="ANNULE">Annuler</button>
      </div>`;
  }

  item.innerHTML = `
    <div>
      <div>Patient #${r.patient_id} — Médecin #${r.medecin_id}</div>
      <div class="meta">${date}${r.motif ? " · " + r.motif : ""}</div>
    </div>
    <span class="badge badge-${r.statut}">${r.statut.replace("_", " ")}</span>
    ${actionsHtml}
  `;

  item.querySelectorAll("button[data-id]").forEach(btn => {
    btn.addEventListener("click", async () => {
      try {
        await api(`/rendezvous/${btn.dataset.id}`, {
          method: "PATCH",
          body: { statut: btn.dataset.statut },
        });
        const filtreActif = document.querySelector(".chip-filter.active")?.dataset.statut || "";
        chargerRdvStaff(filtreActif);
      } catch (err) {
        alert(err.message);
      }
    });
  });

  return item;
}

// ==========================================================
// Espace médecin — RDV, consultation, prescription, disponibilités
// ==========================================================
let rdvEnCoursDeConsultation = null;   // id du RDV en cours de traitement
let consultationCreeeId = null;        // id de la consultation, une fois créée
let listeMedicamentsCache = null;      // cache pour éviter de re-fetch à chaque ouverture

document.querySelectorAll(".chip-filter-medecin").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".chip-filter-medecin").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    chargerRdvMedecin(btn.dataset.statut);
  });
});

async function chargerRdvMedecin(statut) {
  const conteneur = document.getElementById("liste-rdv-medecin");
  conteneur.innerHTML = "";
  const query = statut ? `?statut=${statut}` : "";
  const rdvs = await api("/rendezvous" + query);
  if (rdvs.length === 0) {
    conteneur.innerHTML = `<span class="empty">Aucun rendez-vous dans cette catégorie.</span>`;
    return;
  }
  rdvs.forEach(r => conteneur.appendChild(carteRdvMedecin(r)));
}

function carteRdvMedecin(r) {
  const item = document.createElement("div");
  item.className = "list-item";
  const date = new Date(r.date_heure).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });

  let actionsHtml = "";
  if (r.statut === "CONFIRME" || r.statut === "EN_COURS") {
    actionsHtml = `
      <div class="actions">
        <button class="btn-mini confirm" data-ouvrir-consultation="${r.id}">Enregistrer consultation</button>
      </div>`;
  }

  item.innerHTML = `
    <div>
      <div>Patient #${r.patient_id}</div>
      <div class="meta">${date}${r.motif ? " · " + r.motif : ""}</div>
    </div>
    <span class="badge badge-${r.statut}">${r.statut.replace("_", " ")}</span>
    ${actionsHtml}
  `;

  const btnConsult = item.querySelector("[data-ouvrir-consultation]");
  if (btnConsult) {
    btnConsult.addEventListener("click", () => ouvrirFormulaireConsultation(r.id));
  }

  return item;
}

function ouvrirFormulaireConsultation(rdvId) {
  rdvEnCoursDeConsultation = rdvId;
  consultationCreeeId = null;
  document.getElementById("consultation-rdv-id").textContent = rdvId;
  document.getElementById("consultation-compte-rendu").value = "";
  document.getElementById("consultation-message").textContent = "";
  document.getElementById("carte-consultation").classList.remove("hidden");
  document.getElementById("carte-prescription").classList.add("hidden");
  document.getElementById("carte-consultation").scrollIntoView({ behavior: "smooth" });
}

document.getElementById("btn-annuler-consultation").addEventListener("click", () => {
  document.getElementById("carte-consultation").classList.add("hidden");
  rdvEnCoursDeConsultation = null;
});

document.getElementById("btn-valider-consultation").addEventListener("click", async () => {
  const message = document.getElementById("consultation-message");
  const compteRendu = document.getElementById("consultation-compte-rendu").value.trim();
  if (!compteRendu) {
    message.textContent = "Le compte-rendu ne peut pas être vide.";
    return;
  }

  // Étape 1 : enregistrer la consultation.
  try {
    const reponse = await api(`/consultations/${rdvEnCoursDeConsultation}`, {
      method: "POST",
      body: { compte_rendu: compteRendu },
    });
    consultationCreeeId = reponse.id;
    message.textContent = "Consultation enregistrée avec succès.";
  } catch (err) {
    message.textContent = "Erreur lors de l'enregistrement : " + err.message;
    return; // on s'arrête ici si cette étape échoue — pas de prescription possible sans consultation.
  }

  // Étape 2 : ouvrir le formulaire de prescription (indépendante — si elle échoue,
  // l'erreur reste visible au lieu de disparaître avec la carte masquée).
  try {
    document.getElementById("carte-consultation").classList.add("hidden");
    await ouvrirFormulairePrescription();
    chargerRdvMedecin(document.querySelector(".chip-filter-medecin.active")?.dataset.statut || "");
  } catch (err) {
    document.getElementById("carte-consultation").classList.remove("hidden");
    message.textContent = "Consultation enregistrée, mais le formulaire de prescription n'a pas pu s'ouvrir : " + err.message;
  }
});

// ---------- Prescription ----------
async function chargerMedicaments() {
  if (!listeMedicamentsCache) {
    listeMedicamentsCache = await api("/medicaments");
  }
  return listeMedicamentsCache;
}

async function ouvrirFormulairePrescription() {
  const medicaments = await chargerMedicaments();
  const conteneur = document.getElementById("lignes-prescription");
  conteneur.innerHTML = "";
  document.getElementById("prescription-message").textContent = "";
  ajouterLignePrescription(medicaments);
  document.getElementById("carte-prescription").classList.remove("hidden");
  document.getElementById("carte-prescription").scrollIntoView({ behavior: "smooth" });
}

function ajouterLignePrescription(medicaments) {
  const conteneur = document.getElementById("lignes-prescription");
  const ligne = document.createElement("div");
  ligne.className = "grid-2";
  ligne.style.marginBottom = "8px";
  ligne.innerHTML = `
    <label>Médicament
      <select class="ligne-medicament">
        ${medicaments.map(m => `<option value="${m.id}">${m.nom}</option>`).join("")}
      </select>
    </label>
    <label>Posologie
      <input type="text" class="ligne-posologie" placeholder="ex. 1 comprimé matin et soir">
    </label>
  `;
  conteneur.appendChild(ligne);
}

document.getElementById("btn-ajouter-ligne").addEventListener("click", async () => {
  const medicaments = await chargerMedicaments();
  ajouterLignePrescription(medicaments);
});

document.getElementById("btn-ignorer-prescription").addEventListener("click", () => {
  document.getElementById("carte-prescription").classList.add("hidden");
  consultationCreeeId = null;
});

document.getElementById("btn-valider-prescription").addEventListener("click", async () => {
  const message = document.getElementById("prescription-message");
  const lignesEl = document.querySelectorAll("#lignes-prescription .grid-2");
  const lignes = Array.from(lignesEl).map(el => ({
    medicament_id: Number(el.querySelector(".ligne-medicament").value),
    posologie: el.querySelector(".ligne-posologie").value.trim(),
  })).filter(l => l.posologie);

  if (lignes.length === 0) {
    message.textContent = "Ajoutez au moins une ligne avec une posologie renseignée.";
    return;
  }
  try {
    await api("/prescriptions", {
      method: "POST",
      body: { consultation_id: consultationCreeeId, lignes },
    });
    message.textContent = "Prescription enregistrée avec succès.";
    setTimeout(() => document.getElementById("carte-prescription").classList.add("hidden"), 1200);
  } catch (err) {
    message.textContent = err.message;
  }
});

// ---------- Disponibilités ----------
document.getElementById("btn-ajouter-dispo").addEventListener("click", async () => {
  const message = document.getElementById("dispo-message");
  try {
    await api("/medecins/moi/disponibilites", {
      method: "POST",
      body: {
        jour_semaine: Number(document.getElementById("dispo-jour").value),
        heure_debut: document.getElementById("dispo-debut").value,
        heure_fin: document.getElementById("dispo-fin").value,
        duree_creneau_minutes: Number(document.getElementById("dispo-duree").value),
      },
    });
    message.textContent = "Disponibilité ajoutée.";
    chargerMesDisponibilites();
  } catch (err) {
    message.textContent = err.message;
  }
});

const JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];

async function chargerMesDisponibilites() {
  const conteneur = document.getElementById("liste-dispos");
  conteneur.innerHTML = "";
  const dispos = await api("/medecins/moi/disponibilites");
  if (dispos.length === 0) {
    conteneur.innerHTML = `<span class="empty">Aucune disponibilité déclarée pour le moment.</span>`;
    return;
  }
  dispos.forEach(d => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `<div>${JOURS[d.jour_semaine]} — ${d.heure_debut} à ${d.heure_fin}
      <span class="meta">(créneaux de ${d.duree_creneau_minutes} min)</span></div>`;
    conteneur.appendChild(item);
  });
}

// ==========================================================
// Espace administrateur — comptes, dashboard, supervision, patients, médicaments
// ==========================================================

// ---------- Tableau de bord ----------
async function chargerTableauDeBord() {
  const cartes = document.getElementById("dashboard-cartes");
  const occupation = document.getElementById("dashboard-occupation");
  const alertes = document.getElementById("dashboard-alertes");
  try {
    const d = await api("/gestion-admin/tableau-de-bord");
    const tuile = (valeur, label) => `<div class="dashboard-tuile"><div class="valeur">${valeur}</div><div class="label">${label}</div></div>`;

    cartes.innerHTML =
      tuile(Object.values(d.rdv_aujourdhui).reduce((a, b) => a + b, 0), "RDV aujourd'hui") +
      tuile(Object.values(d.rdv_semaine).reduce((a, b) => a + b, 0), "RDV cette semaine") +
      tuile(d.rdv_aujourdhui.EN_ATTENTE || 0, "En attente (jour)") +
      tuile(d.nouveaux_patients_7j, "Nouveaux patients (7j)") +
      tuile(d.rdv_annules_30j, "Annulés (30j)");

    let tableauHtml = `<table class="table-occupation"><tr><th>Médecin</th><th>Spécialité</th><th>Créneaux/sem.</th><th>RDV pris</th><th>Occupation</th></tr>`;
    d.taux_occupation_par_medecin.forEach(m => {
      tableauHtml += `<tr><td>${m.medecin}</td><td>${m.specialite}</td><td>${m.creneaux_semaine}</td><td>${m.rdv_pris_semaine}</td><td>${m.taux_occupation_pct}%</td></tr>`;
    });
    tableauHtml += `</table>`;
    occupation.innerHTML = tableauHtml;

    alertes.textContent = d.alertes.demandes_en_attente_plus_48h > 0
      ? `⚠️ ${d.alertes.demandes_en_attente_plus_48h} demande(s) en attente depuis plus de 48h.`
      : "Aucune alerte en cours.";
  } catch (err) {
    cartes.innerHTML = `<span class="empty">Erreur de chargement du tableau de bord : ${err.message}</span>`;
  }
}

// ---------- Gestion des utilisateurs ----------
document.getElementById("admin-filtre-role").addEventListener("change", () => chargerUtilisateurs());
document.getElementById("admin-filtre-actif").addEventListener("change", () => chargerUtilisateurs());

async function chargerUtilisateurs() {
  const conteneur = document.getElementById("liste-utilisateurs");
  conteneur.innerHTML = "";
  const role = document.getElementById("admin-filtre-role").value;
  const actif = document.getElementById("admin-filtre-actif").value;
  const params = new URLSearchParams();
  if (role) params.set("role", role);
  if (actif) params.set("actif", actif);

  try {
    const utilisateurs = await api("/gestion-admin/utilisateurs?" + params.toString());
    if (utilisateurs.length === 0) {
      conteneur.innerHTML = `<span class="empty">Aucun utilisateur ne correspond à ces filtres.</span>`;
      return;
    }
    utilisateurs.forEach(u => conteneur.appendChild(carteUtilisateur(u)));
  } catch (err) {
    conteneur.innerHTML = `<span class="empty">Erreur : ${err.message}</span>`;
  }
}

function carteUtilisateur(u) {
  const item = document.createElement("div");
  item.className = "list-item";
  const date = new Date(u.date_creation).toLocaleDateString("fr-FR");
  item.innerHTML = `
    <div>
      <div>${u.prenom} ${u.nom} — ${u.email}</div>
      <div class="meta">${u.role} · inscrit le ${date} · ${u.is_active ? "actif" : "désactivé"}</div>
    </div>
    <div class="actions">
      <button class="btn-mini ${u.is_active ? "cancel" : "confirm"}" data-toggle-actif="${u.id}" data-etat="${u.is_active}">
        ${u.is_active ? "Désactiver" : "Réactiver"}
      </button>
      <button class="btn-mini confirm" data-reset-password="${u.id}">Réinit. mdp</button>
    </div>
  `;

  item.querySelector("[data-toggle-actif]").addEventListener("click", async (e) => {
    const id = e.target.dataset.toggleActif;
    const etatActuel = e.target.dataset.etat === "true";
    try {
      await api(`/gestion-admin/utilisateurs/${id}`, { method: "PATCH", body: { is_active: !etatActuel } });
      chargerUtilisateurs();
    } catch (err) {
      alert(err.message);
    }
  });

  item.querySelector("[data-reset-password]").addEventListener("click", async (e) => {
    const id = e.target.dataset.resetPassword;
    const nouveau = prompt("Nouveau mot de passe (6 caractères minimum) :");
    if (!nouveau) return;
    try {
      await api(`/gestion-admin/utilisateurs/${id}/mot-de-passe`, { method: "POST", body: { nouveau_mot_de_passe: nouveau } });
      alert("Mot de passe réinitialisé avec succès.");
    } catch (err) {
      alert(err.message);
    }
  });

  return item;
}

// ---------- Création de compte ----------
document.getElementById("btn-ouvrir-creation-compte").addEventListener("click", () => {
  document.getElementById("carte-creation-compte").classList.remove("hidden");
});
document.getElementById("btn-annuler-creation-compte").addEventListener("click", () => {
  document.getElementById("carte-creation-compte").classList.add("hidden");
});
document.getElementById("nc-role").addEventListener("change", (e) => {
  document.getElementById("nc-specialite-wrap").classList.toggle("hidden", e.target.value !== "MEDECIN");
});

document.getElementById("btn-valider-creation-compte").addEventListener("click", async () => {
  const message = document.getElementById("creation-compte-message");
  try {
    await api("/gestion-admin/utilisateurs", {
      method: "POST",
      body: {
        prenom: document.getElementById("nc-prenom").value,
        nom: document.getElementById("nc-nom").value,
        email: document.getElementById("nc-email").value,
        mot_de_passe: document.getElementById("nc-motdepasse").value,
        role: document.getElementById("nc-role").value,
        specialite: document.getElementById("nc-specialite").value,
      },
    });
    message.textContent = "Compte créé avec succès.";
    chargerUtilisateurs();
    setTimeout(() => document.getElementById("carte-creation-compte").classList.add("hidden"), 1000);
  } catch (err) {
    message.textContent = err.message;
  }
});

// ---------- Supervision transverse des RDV ----------
document.querySelectorAll(".chip-filter-admin-rdv").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".chip-filter-admin-rdv").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    chargerRdvAdmin(btn.dataset.statut);
  });
});

async function chargerRdvAdmin(statut) {
  const conteneur = document.getElementById("liste-rdv-admin");
  conteneur.innerHTML = "";
  const query = statut ? `?statut=${statut}` : "";
  const rdvs = await api("/rendezvous" + query);
  const medecins = await api("/medecins");

  if (rdvs.length === 0) {
    conteneur.innerHTML = `<span class="empty">Aucun rendez-vous dans cette catégorie.</span>`;
    return;
  }
  rdvs.forEach(r => {
    const item = document.createElement("div");
    item.className = "list-item";
    const date = new Date(r.date_heure).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
    const options = medecins.map(m => `<option value="${m.id}" ${m.id === r.medecin_id ? "selected" : ""}>Dr ${m.prenom} ${m.nom}</option>`).join("");
    item.innerHTML = `
      <div>
        <div>Patient #${r.patient_id}</div>
        <div class="meta">${date}${r.motif ? " · " + r.motif : ""}</div>
      </div>
      <span class="badge badge-${r.statut}">${r.statut.replace("_", " ")}</span>
      <select class="select-reaffectation" data-rdv-id="${r.id}">${options}</select>
    `;
    item.querySelector(".select-reaffectation").addEventListener("change", async (e) => {
      try {
        await api(`/rendezvous/${r.id}`, { method: "PATCH", body: { nouveau_medecin_id: Number(e.target.value) } });
        chargerRdvAdmin(statut);
      } catch (err) {
        alert(err.message);
      }
    });
    conteneur.appendChild(item);
  });
}

// ---------- Recherche patient / dossier ----------
let delaiRecherche = null;
document.getElementById("admin-recherche-patient").addEventListener("input", (e) => {
  clearTimeout(delaiRecherche);
  delaiRecherche = setTimeout(() => rechercherPatients(e.target.value), 300);
});

async function rechercherPatients(terme) {
  const conteneur = document.getElementById("resultats-recherche-patient");
  conteneur.innerHTML = "";
  if (!terme || terme.trim().length < 2) return;

  const resultats = await api(`/gestion-admin/patients?q=${encodeURIComponent(terme)}`);
  resultats.forEach(p => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.style.cursor = "pointer";
    item.innerHTML = `<div>${p.prenom} ${p.nom} <span class="meta">— ${p.email}</span></div>`;
    item.addEventListener("click", () => afficherDossierPatient(p.id));
    conteneur.appendChild(item);
  });
}

async function afficherDossierPatient(patientId) {
  const conteneur = document.getElementById("dossier-patient");
  conteneur.innerHTML = "Chargement...";
  const dossier = await api(`/gestion-admin/patients/${patientId}/dossier`);

  let html = `<h3 style="margin-bottom:8px;">${dossier.patient.prenom} ${dossier.patient.nom} — ${dossier.patient.email}</h3>`;
  html += `<p class="hint">Rendez-vous (${dossier.rendez_vous.length})</p><div class="list">`;
  dossier.rendez_vous.forEach(r => {
    const date = new Date(r.date_heure).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
    html += `<div class="list-item"><div>${date}${r.motif ? " · " + r.motif : ""}</div><span class="badge badge-${r.statut}">${r.statut.replace("_", " ")}</span></div>`;
  });
  html += `</div><p class="hint" style="margin-top:10px;">Prescriptions (${dossier.prescriptions.length})</p><div class="list">`;
  dossier.prescriptions.forEach(p => {
    const meds = p.lignes.map(l => `${l.medicament} (${l.posologie})`).join(", ");
    html += `<div class="list-item"><div>${meds}</div></div>`;
  });
  html += `</div>`;
  conteneur.innerHTML = html;
}

// ---------- Référentiel médicaments ----------
async function chargerMedicamentsAdmin() {
  const conteneur = document.getElementById("liste-medicaments-admin");
  conteneur.innerHTML = "";
  const medicaments = await api("/medicaments");
  medicaments.forEach(m => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `<div>${m.nom}</div><button class="btn-mini cancel" data-supprimer-med="${m.id}">Supprimer</button>`;
    item.querySelector("[data-supprimer-med]").addEventListener("click", async () => {
      try {
        await api(`/gestion-admin/medicaments/${m.id}`, { method: "DELETE" });
        chargerMedicamentsAdmin();
      } catch (err) {
        alert(err.message);
      }
    });
    conteneur.appendChild(item);
  });
}

document.getElementById("btn-ajouter-medicament").addEventListener("click", async () => {
  const champ = document.getElementById("admin-med-nom");
  if (!champ.value.trim()) return;
  try {
    await api("/gestion-admin/medicaments", { method: "POST", body: { nom: champ.value.trim() } });
    champ.value = "";
    chargerMedicamentsAdmin();
  } catch (err) {
    alert(err.message);
  }
});

// ==========================================================
// Démarrage
// ==========================================================
if (session.token && session.role) {
  majEnteteUtilisateur();
  afficherVue(session.role);
} else {
  afficherVue(null);
}
