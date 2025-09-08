document.addEventListener("DOMContentLoaded", function () {
  // Remove footer version node if present
  var footerNode = document.querySelector(".main-footer .float-right")
                 || document.querySelector(".main-footer .d-none.d-sm-inline")
                 || document.querySelector("footer .float-right");
  if (footerNode) footerNode.remove();

  // Enforce login logo size (in case CSS is cached)
  var loginImg = document.querySelector(".login-logo img");
  if (loginImg) {
    loginImg.style.maxWidth = "180px";
    loginImg.style.height = "auto";
  }
});
