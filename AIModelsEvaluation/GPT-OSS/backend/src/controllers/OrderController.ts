import { Request, Response, Router } from "express";
import { OrderService } from "../services/OrderService";

const router = Router();
const service = new OrderService();

router.get("/", async (_req: Request, res: Response) => {
  res.json(await service.getAll());
});

router.get("/:id", async (req: Request, res: Response) => {
  res.json(await service.getById(req.params.id));
});

router.post("/", async (req: Request, res: Response) => {
  const { customerId, items } = req.body;
  res.status(201).json(await service.create(customerId, items));
});

router.put("/:id/accept", async (req: Request, res: Response) => {
  res.json(await service.accept(req.params.id));
});

router.put("/:id/ship", async (req: Request, res: Response) => {
  res.json(await service.ship(req.params.id));
});

router.put("/:id/close", async (req: Request, res: Response) => {
  res.json(await service.close(req.params.id));
});

router.put("/:id", async (req: Request, res: Response) => {
  res.json(await service.update(req.params.id, req.body));
});

router.delete("/:id", async (req: Request, res: Response) => {
  res.json(await service.delete(req.params.id));
});

export default router;