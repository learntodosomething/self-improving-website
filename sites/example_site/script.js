function highlight() {
  var msg = "Bouquet selected: " + document.querySelector(".hero h1").textContent;
  document.querySelector(".hero").innerHTML += "<p class='note'>" + msg + "</p>";
}

function submitForm() {
  alert("Thanks! We will contact you soon.");
}
