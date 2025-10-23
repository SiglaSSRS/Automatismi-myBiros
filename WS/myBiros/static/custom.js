///   C A R I C A M E N T O   /////////////////////////////////////////

function spinner(id, idEsito){ // rende visibile l'overlay di caricamento
    document.getElementById(id).style.visibility="visible";  
    document.getElementById(id).style.display="flex";

    const alerts = document.getElementsByClassName("alert")
    if (alerts) {
        for (let i = 0; i < alerts.length; i++) {
            alerts[i].style.display="none";
        }
    }

    const esito = document.getElementById(idEsito)
    if (esito) {esito.style.display="none";}
}

function navigate() {
    window.location.href = 'result';
}
fetch('analizza').then(navigate);