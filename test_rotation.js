
const ezW = document.getElementById("ezviz").clientWidth;
const isPortrait = d.ezviz.rotation === "90" || d.ezviz.rotation === "-90";
const ezH = isPortrait ? Math.round(ezW * 16 / 9) : Math.round(ezW * 9 / 16);

// But EZUIKit expects width and height.
// If we pass the unrotated dimensions to EZUIKit, we can style it via CSS.

