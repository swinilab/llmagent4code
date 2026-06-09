function copyToClipboard(btn) {
  const input = btn.previousElementSibling;
  input.select();
  document.execCommand('copy');
  
  const oldText = btn.innerText;
  btn.innerText = 'Copied!';
  setTimeout(() => {
    btn.innerText = oldText;
  }, 2000);
}
