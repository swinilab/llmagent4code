import QRCode from 'qrcode';

export async function generateQR(url) {
  return QRCode.toBuffer(url, {
    errorCorrectionLevel: 'H',
    type: 'image/png',
    quality: 0.95,
    margin: 1,
    width: 300
  });
}
