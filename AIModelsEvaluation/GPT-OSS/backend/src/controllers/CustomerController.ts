import { Request, Response, Router } from "express";
import { CustomerService } from "../services/CustomerService";

const router = Router();
const service = new CustomerService();

router.get("/", async (_req: Request, res: Response) => {
  res.json(await service.getAll());
});

router.get("/:id", async (req: Request, res: Response) => {
  res.json(await service.getById(req.params.id));
});

router.post("/", async (req: Request, res: Response) => {
  res.status(201).json(await service.create(req.body));
});

router.put("/:id", async (req: Request, res: Response) => {
  res.json(await service.update(req.params.id, req.body));
});

router.delete("/:id", async (req: Request, res: Response) => {
  res.json(await service.delete(req.params.id));
});

export default router;