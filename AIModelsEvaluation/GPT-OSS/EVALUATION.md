# GPT-OSS EVALUATION

## Domain Entities

5 domain entities are present: ```Customer```, ```Invoice```, ```Order```, ```Payment```, ```Product```.

## Domain Attributes

- Count: ```35```

GPT-OSS missed ```17``` domain attributes compared to the original benchmark application.

- List of missing attributes
  - ```createdAt```, ```updatedAt```, ```orders``` in ```Customer```
  - ```date```, ```method```, ```updatedAt``` in ```Invoice```
  - ```customerName```, ```customerAddress```, ```customerPhone```, ```customerBankAccount```, ```method```, ```orderDate``` in ```Order```
  - ```date```, ```updatedAt``` in ```Payment```
  - ```image```, ```createdAt```, ```updatedAt``` in ```Product```

- Types: ```6```
  - ```Number```
  - ```Date```
  - ```String```
  - ```Array```
  - ```Class```
  - ```Enum```

    in ```TypeScript```.

- Missing Type: ```Interface``` compared to the benchmark app.

## Relationships between Domain Models

- Count: ```4```
  - ```Customer``` to ```Order``` (One-to-Many)
  - ```Product``` to ```Order``` (One-to-Many)
  - ```Order``` to ```Invoice``` (One-to-Many)
  - ```Invoice``` to ```Payment``` (One-to-Many)

GPT-OSS missed ```4``` relationship compared to the original benchmark application.

- List of missing relationships
  - ```Order``` to ```Customer```
  - ```Order``` to ```Product```
  - ```Payment``` to ```Invoice```
  - ```Invoice``` to ```Order```

## Architectural Alignment

GPT-OSS did not follow the established domain-driven architecture. The domain models are scattered across both in  ```frontend/src/domain/``` and ```backend/src/domain/``` subfolders instead of in their own directory, violating the architectural rules of the app.

However, GPT-OSS still succeeded in implementing encapsulation between layers, with the Domain Models correctly handled their responsibilities (which is only to define the technical representation of the models and their attributes).