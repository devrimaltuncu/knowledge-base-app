---
title: Project Alpha
tags:
  - project
  - architecture
date: 2026-07-01
---

# Project Alpha - Architecture Document

## Overview

Project Alpha is our flagship product that combines [[Machine Learning]] with a modern web stack.

## Tech Stack

- **Frontend**: React, Tailwind CSS
- **Backend**: [[Python Tips|Python]] with FastAPI
- **Database**: PostgreSQL
- **ML Pipeline**: Scikit-learn + PyTorch

## Design Decisions

1. **Microservices over Monolith** - Better scalability
2. **Event-driven architecture** - Using message queues
3. **API-first design** - All features exposed via REST

## Key Components

| Component | Tech | Status |
|-----------|------|--------|
| User Service | FastAPI | Done |
| ML Service | Python | In Progress |
| Data Pipeline | [[Data Engineering]] | Planned |

## Links

- [[Home]] - Back to home
- [[DevOps Guide]] - Deployment procedures