import { Request, Response, Router } from "express";
import { PaymentService } from "../services/PaymentService";

const router = Router();
const service = new PaymentService();

router.get("/", async (_req: Request, res: Response) => {
  res.json(await service.getAll());
});

router.get("/:id", async (req: Request, res: Response) => {
  res.json(await service.getById(req.params.id));
});

router.post("/", async (req: Request, res: Response) => {
  const { invoiceId, amount, method } = req.body;
  res.status(201).json(await service.makePayment(invoiceId, amount, method));
});

router.put("/:id", async (req: Request, res: Response) => {
  res.json(await service.update(req.params.id, req.body));
});

router.delete("/:id", async (req: Request, res: Response) => {
  res.json(await service.delete(req.params.id));
});

export default router;