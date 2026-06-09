import nodemailer from 'nodemailer';

let transporter;

if (process.env.SMTP_HOST) {
  transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: process.env.SMTP_PORT || 587,
    secure: false,
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS
    }
  });
} else {
  transporter = {
    sendMail: async (mailOptions) => {
      console.log('[EMAIL]', `To: ${mailOptions.to}`);
      console.log('[EMAIL]', `Subject: ${mailOptions.subject}`);
      console.log('[EMAIL]', mailOptions.html || mailOptions.text);
      return { messageId: 'test' };
    }
  };
}

export async function sendMail(to, subject, html, text) {
  try {
    await transporter.sendMail({
      from: process.env.SMTP_FROM,
      to,
      subject,
      html,
      text
    });
  } catch (err) {
    console.error('Email send error:', err);
  }
}
