# JMeter load test (Apache JMeter 5.6)

A parameterised load test against the public [DummyJSON](https://dummyjson.com)
API. One test plan covers a smoke check with 2 users and a load profile with
50 users. Nothing in the `.jmx` file needs editing between runs.

## What the plan does

Each virtual user runs this sequence per loop, with a think time between
requests:

1. `GET /products?limit=10&skip=0`. Asserts status 200 and that the page
   holds 10 products.
2. `GET /products/{id}`. The id comes from `data/product_ids.csv`, shared
   across users and recycled. Asserts status 200 and that the returned id is
   the one requested.
3. `POST /auth/login` with the public demo account (`emilys` /
   `emilyspass`). Asserts status 200 and extracts `accessToken` with a JSON
   Extractor.
4. `GET /auth/me` with `Authorization: Bearer <token>`. Asserts status 200
   and that the returned username is the one that logged in.

Every request also carries a Duration Assertion. A response slower than the
SLA (default 2000 ms) counts as an error, so slow responses show up in the
error rate and not only in the percentiles.

## Run it

Install [Apache JMeter 5.6](https://jmeter.apache.org/download_jmeter.cgi)
and put `bin/` on your PATH, or set `JMETER_HOME`.

```bash
cd jmeter
./run.sh                                   # smoke: 2 users, 1 loop
THREADS=20 RAMP_UP=20 LOOPS=10 ./run.sh    # load: 20 users, 10 loops each
SLA_MS=1000 ./run.sh                       # tighter SLA
```

Each run writes to `results/<timestamp>/`:

- `results.jtl`, the raw sample log (CSV)
- `dashboard/index.html`, the JMeter HTML report
- `jmeter.log`

Without the script, the same run is:

```bash
jmeter -n -t test-plans/dummyjson_load_test.jmx \
  -l results/results.jtl -e -o results/dashboard \
  -Jthreads=20 -Jramp_up=20 -Jloops=10 -Jsla_ms=2000
```

Properties the plan reads (`-Jname=value`):

| Property | Default | Meaning |
|---|---|---|
| `host` | `dummyjson.com` | Target host |
| `protocol` | `https` | Scheme |
| `threads` | `5` | Virtual users |
| `ramp_up` | `5` | Seconds to start all users |
| `loops` | `10` | Iterations per user |
| `think_time_ms` | `300` | Pause before each request |
| `sla_ms` | `2000` | Duration Assertion limit |
| `csv_path` | `../data/product_ids.csv` | Product ids, relative to the plan |
| `username`, `password` | demo account | Login body |

## How to read the dashboard

Open `dashboard/index.html`. Start with the Statistics table.

- Error %: must be 0. An error here is a failed assertion, an HTTP error, or
  a response over the SLA.
- 90th and 95th percentile: the numbers to compare between runs. The average
  hides the slow tail.
- Throughput: requests per second the target handled at this load. Compare
  it with the user count. If users double and throughput does not, the
  target is saturating.
- Response Times Over Time (Charts tab): a rising line at a flat user count
  means a queue is building somewhere.

Suggested pass criteria for this API:

| Metric | Limit |
|---|---|
| Error % | 0 |
| 95th percentile | under 1500 ms |
| 99th percentile | under 2500 ms |

## Scaling the load safely

This is a free public API shared by many people. Keep runs small: no more
than 20 users and 10 loops, with the default think time. The plan is a
template. Point `host` at your own environment before you raise the load.

Good practice when you do:

1. Run the smoke profile first. It proves the plan and the environment.
2. Raise users in steps (5, 10, 20, 50) and keep the ramp up equal to the
   user count in seconds.
3. Keep the think time. Zero think time measures the tool, not the users.
4. Watch the target's own metrics (CPU, memory, pod count, database
   connections) next to the JMeter numbers. The bottleneck is usually visible
   there before it shows in the percentiles.

## Verified run

The plan was run from this repository with the smoke profile and a 3 user, 2
loop profile. Both runs finished with 0 errors and produced the dashboard.
