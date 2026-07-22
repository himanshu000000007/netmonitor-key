# Network Device Monitoring Dashboard

Flask + PostgreSQL app jo network devices (RF devices, routers, switches) ka
status track karta hai — ping karke up/down dikhata hai.

## Phase 1 — Local mein chalana (Docker Compose)

Iske liye tumhare laptop/WSL par Docker Desktop install hona chahiye.

```bash
cd network-monitor
docker compose up --build
```

Ye ek saath 2 containers start karega:
- `netmonitor-db` — Postgres database
- `netmonitor-web` — Flask app (gunicorn ke saath)

Browser mein kholo: `http://localhost`

Band karne ke liye:
```bash
docker compose down          # containers band, data (volume) safe rehta hai
docker compose down -v       # containers + saara data delete (fresh start)
```

## Kaise kaam karta hai (Docker Compose ka concept)

`docker-compose.yml` file define karti hai ki kaunse containers chahiye aur
wo ek-doosre se kaise baat karenge:

- `db` service Postgres image use karti hai, data ek **named volume**
  (`postgres_data`) mein store hota hai — container restart/rebuild hone par
  bhi data safe rehta hai.
- `web` service apni khud ki Dockerfile se build hoti hai, aur `DB_HOST=db`
  environment variable ke through Postgres se connect hoti hai. Docker
  Compose automatically ek internal network banata hai jisme container naam
  hi hostname ban jaata hai — isliye `db` sirf naam se resolve ho jaata hai,
  IP address ki zaroorat nahi.
- `depends_on` + `healthcheck` ensure karta hai ki Flask app tabhi start ho
  jab Postgres fully ready ho (warna race condition ho sakta hai jahan app
  pehle start ho jaaye aur DB abhi ready na ho).

## Agla Phase

- **Phase 2**: Terraform se AWS infra (EC2 + Security Group) code se banana
- **Phase 3**: Prometheus + Grafana add karna monitoring ke liye
- **Phase 4**: k3s (lightweight Kubernetes) par deploy karna
