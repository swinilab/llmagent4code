# PHI EVALUATION

## Domain Entities

5 domain entities are present: ```Customer```, ```Invoice```, ```Order```, ```Payment```, ```Product```.

## Domain Attributes

- Count: ```36```

Phi missed ```14``` domain attributes compared to the original benchmark application.

- List of missing attributes
  - ```createdAt```, ```updatedAt``` in ```Customer```
  - ```method```, ```createdAt```, ```updatedAt``` in ```Invoice```
  - ```method```, ```createdAt```, ```updatedAt``` in ```Order```
  - ```invoiceId```, ```createdAt```, ```updatedAt``` in ```Payment```
  - ```image```, ```createdAt```, ```updatedAt``` in ```Product```

- Types: ```5```
  - ```Number```
  - ```String```
  - ```Array```
  - ```Class```
  - ```Interface```

    in ```TypeScript```.

- Missing Type: ```Date``` compared to the benchmark app.

## Relationships between Domain Models

- Count: ```5```
  - ```Customer``` to ```Order``` (One-to-Many)
  - ```Payment``` to ```Order``` (One-to-One)
  - ```Order``` to ```Product``` (One-to-Many)
  - ```Order``` to ```Customer``` (One-to-One)
  - ```Order``` to ```Invoice``` (One-to-One)

Phi missed ```2``` relationship compared to the original benchmark application.

- List of missing relationships
  - ```Invoice``` to ```Order```
  - ```Payment``` to ```Invoice```

## Architectural Alignment

Phi successfully followed the established domain-driven architecture, with proper folder and project structure. The domain models are stored in a distinct ```modules/``` directory, separated from the backend and frontend modules.

Encapsulation between layers are clear and concise, with the Domain Models correctly handled their responsibilities (which is only to define the technical representation of the models and their attributes).