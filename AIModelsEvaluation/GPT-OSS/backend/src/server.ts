import { AppDataSource } from "./db";
import { app } from "./app";

const PORT = process.env.PORT ?? 4000;

AppDataSource.initialize()
  .then(() => {
    console.log("🚀 Database ready");
    app.listen(PORT, () => {
      console.log(`🚀 Server listening on http://localhost:${PORT}`);
    });
  })
  .catch((err) => {
    console.error("❌ Database connection error", err);
  });