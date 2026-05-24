# GEMMA EVALUATION

## Domain Entities

5 domain entities are present: ```Customer```, ```Invoice```, ```Order```, ```Payment```, ```Product```.

## Domain Attributes

- Count: ```29```

Gemma missed ```18``` domain attributes compared to the original benchmark application.

- List of missing attributes
  - ```createdAt```, ```updatedAt``` in ```Customer```
  - ```method```, ```createdAt```, ```updatedAt``` in ```Invoice```
  - ```customerName```, ```customerAddress```, ```customerPhone```, ```customerBankAccount```, ```method```,```createdAt```, ```updatedAt``` in ```Order```
  - ```createdAt```, ```updatedAt``` in ```Payment```
  - ```name```, ```image```, ```createdAt```, ```updatedAt``` in ```Product```

- Types: ```7```
  - ```Integer```
  - ```String```
  - ```List```
  - ```Optional```
  - ```Datetime```
  - ```Float```
  - ```Class```

    in ```Python```.

- Missing Type: ```Interface/Abstract Class``` compared to the benchmark app.

## Relationships between Domain Models

- Count: ```6```
  - ```Customer``` to ```Order``` (One-to-Many)
  - ```Order``` to ```Invoice``` (One-to-One)
  - ```Order``` to ```Customer``` (One-to-One)
  - ```Payment``` to ```Invoice``` (One-to-One)
  - ```Invoice``` to ```Order``` (One-to-One)
  - ```Invoice``` to ```Customer``` (One-to-One)

Gemma missed ```1``` relationship compared to the original benchmark application.

- List of missing relationships
  - ```Order``` to ```Product```

## Architectural Alignment

Gemma did not follow the established domain-driven architecture. The domain models are stored in a single ```domain_models.py``` Python file in the ```backend/``` directory instead of in their own, violating the architectural rules of the app.

However, Gemma still succeeded in implementing encapsulation between layers, with the Domain Models correctly handled their responsibilities (which is only to define the technical representation of the models and their attributes).