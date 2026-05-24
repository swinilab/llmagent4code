import { Request, Response, Router } from "express";
import { InvoiceService } from "../services/InvoiceService";
import { OrderService } from "../services/OrderService";

const router = Router();
const service = new InvoiceService();
const orderService = new OrderService();

router.get("/", async (_req: Request, res: Response) => {
  res.json(await service.getAll());
});

router.get("/:id", async (req: Request, res: Response) => {
  res.json(await service.getById(req.params.id));
});

router.post("/from-order/:orderId", async (req: Request, res: Response) => {
  const order = await orderService.getById(req.params.orderId);
  res.status(201).json(await service.create(order));
});

router.put("/:id", async (req: Request, res: Response) => {
  res.json(await service.update(req.params.id, req.body));
});

router.delete("/:id", async (req: Request, res: Response) => {
  res.json(await service.delete(req.params.id));
});

export default router;