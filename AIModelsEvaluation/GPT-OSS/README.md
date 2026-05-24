## 4. Setup & Run Instructions

1. **Clone repository (or copy all files)**  
   All files are already provided – ensure the folder structure matches the code above.

2. **Back‑end**  
   ```bash
   cd backend
   npm install
   npm run dev   # or npm run build && npm start
   ```
   - Server starts on **`http://localhost:4000`**.
   - Database file `order_mgmt.sqlite` will be auto‑created.

3. **Front‑end**  
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   - Front‑end dev server runs on **`http://localhost:5173`** (or whatever Vite picks).
   - All API requests are sent to `http://localhost:4000/api/...`.

4. **Testing the system**  
   - Use the UI to add customers, products, create orders, accept/ship/close them.
   - Generate invoices from orders.
   - Make payments against invoices.
   - Observe status updates in lists.

5. **Deployment**  
   - For production, replace `synchronize: true` with proper migrations.
   - Build front‑end (`npm run build`) and serve the static files with any static host (e.g., Nginx).
   - Proxy API requests to the back‑end or host the API and front‑end separately.

## 5. Extending & Customizing

- **Migrations**: Replace `synchronize: true` with TypeORM migrations for safer production.
- **Authentication**: Add JWT middleware in Express, create a `User` entity and auth service.
- **UI Enhancements**: Use component libraries (Material‑UI, Ant Design) for richer forms.
- **Testing**: Add Jest/React Testing Library tests for UI and supertest for API.

This completes a fully‑functional, minimal Order Management System using a layered architecture, a lightweight SQL database, and a single‑page React front‑end. Enjoy building on top of this foundation!
