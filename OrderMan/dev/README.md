# OVERALL PROJECT STRUCTURE OF THE `DEV` FOLDER.

```txt
.
├── README.md
│
├── backend
│   ├── BackendMain.ts
│   ├── accountant
│   │   ├── AccountantController.ts
│   │   └── AccountantService.ts
│   ├── cart
│   │   ├── CartController.ts
│   │   └── CartService.ts
│   ├── customer
│   │   ├── CustomerController.ts
│   │   └── CustomerService.ts
│   ├── invoice
│   │   ├── InvoiceController.ts
│   │   └── InvoiceService.ts
│   ├── order
│   │   ├── OrderController.ts
│   │   └── OrderService.ts
│   ├── payment
│   │   ├── PaymentController.ts
│   │   └── PaymentService.ts
│   └── product
│       ├── ProductController.ts
│       └── ProductService.ts
│
├── frontend
│   ├── MOSAR Architecture Overview.txt
│   ├── README.md
│   ├── index.html
│   ├── jsconfig.json
│   ├── package-lock.json
│   ├── package.json
│   ├── public
│   │   └── favicon.ico
│   ├── src
│   │   ├── App.vue
│   │   ├── api
│   │   ├── components
│   │   │   ├── accountant
│   │   │   │   └── AccountantView.vue
│   │   │   ├── cart
│   │   │   │   ├── CartField.vue
│   │   │   │   ├── CartModule.vue
│   │   │   │   └── CartView.vue
│   │   │   ├── customer
│   │   │   │   └── CustomerView.vue
│   │   │   ├── invoice
│   │   │   │   └── InvoiceView.vue
│   │   │   ├── order
│   │   │   │   └── OrderView.vue
│   │   │   ├── payment
│   │   │   │   └── PaymentView.vue
│   │   │   ├── product
│   │   │   │   ├── PriceField.vue
│   │   │   │   ├── ProductDetailView.vue
│   │   │   │   ├── ProductField.vue
│   │   │   │   ├── ProductListView.vue
│   │   │   │   └── ProductModule.vue
│   │   │   └── views
│   │   │       ├── CheckoutView.vue
│   │   │       └── NavbarView.vue
│   │   ├── main.js
│   │   ├── index.js
│   │   └── store
│   └── vite.config.js
│
└── modules
    ├── ModuleMain.ts
    ├── accountant
    │   └── AccountantModel.ts
    ├── cart
    │   └── CartModel.ts
    ├── customer
    │   └── CustomerModel.ts
    ├── invoice
    │   └── InvoiceModel.ts
    ├── order
    │   └── OrderModel.ts
    ├── payment
    │   └── PaymentModel.ts
    └── product
        └── ProductModel.ts
```

## EXPLANATION:

1. `backend` folder: For Backend. Use TypeScript and NodeJS.

    In Backend, each of the subfolders contains the Controller and Service TypeScript files, which are responsible for the respective functions that the Backend performs. For example, the `product/` represents the Product module with `ProductController.ts` and `ProductService.ts` files.

2. `frontend` folder: For Frontend.

    In Frontend, each of the subfolders of the `src/components/` directory contains the Vue files for each component (e.g.: `product/` represents the Product component), which represents its view and frontend module.

3. `modules` folder: For the defined modules, used by both frontend and backend. Use TypeScript. These are structured based on the JDA CourseMan app example.

    In this folder, each module should have their own subfolder (e.g.: `product`, `cart`). In each such subfolder, the module has its own model file (e.g.: `cart/CartModel.ts`).

## NOTES:

This folder structure is a standard outline, thus, it is not meant to be heavily modified during the project. Except for the individual files: they are currently bootstrapped/placeholder files, so feel free to edit those.

Only apply necessary and meaningful changes to the folder structure.
