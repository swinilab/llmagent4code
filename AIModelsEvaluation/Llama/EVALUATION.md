# LLAMA EVALUATION

## Domain Entities

5 domain entities are present: ```Customer```, ```Invoice```, ```Order```, ```Payment```, ```Product```.

## Domain Attributes

- Count: ```28```

Llama missed ```20``` domain attributes compared to the original benchmark application.

- List of missing attributes
  - ```createdAt```, ```updatedAt``` in ```Customer```
  - ```orderId```, ```method```, ```createdAt```, ```updatedAt``` in ```Invoice```
  - ```customerName```, ```customerAddress```, ```customerPhone```, ```customerBankAccount```, ```method```,```createdAt```, ```updatedAt``` in ```Order```
  - ```invoiceId```, ```createdAt```, ```updatedAt``` in ```Payment```
  - ```name```, ```image```, ```createdAt```, ```updatedAt``` in ```Product```

- Types: ```5```
  - ```Number```
  - ```Date```
  - ```String```
  - ```Array```
  - ```Interface```

    in ```TypeScript```.

- Missing Type: ```Class``` compared to the benchmark app.

## Relationships between Domain Models

- Count: ```2```
  - ```Customer``` to ```Order``` (One-to-Many)
  - ```Order``` to ```Invoice``` (One-to-One)

Llama missed ```4``` relationship compared to the original benchmark application.

- List of missing relationships
  - ```Order``` to ```Customer```
  - ```Order``` to ```Product```
  - ```Payment``` to ```Invoice```
  - ```Invoice``` to ```Order```

## Architectural Alignment

Llama did not follow the established domain-driven architecture. The domain models are stored in a single ```entities.ts``` TypeScript file in the root folder instead of in their own directory, violating the architectural rules of the app.

However, Llama still succeeded in implementing encapsulation between layers, with the Domain Models correctly handled their responsibilities (which is only to define the technical representation of the models and their attributes).