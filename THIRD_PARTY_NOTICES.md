# Third-party notices

I combined my earlier K-invest (InvestMCP) and Ticker Research projects in this repository. Their project code is MIT licensed; the project copyright identity for this release is ianlyoo. The MIT permission and warranty notice is retained in [LICENSE](LICENSE). No unrelated third-party source code or market-data recordings are vendored.

Runtime packages are installed as dependencies and retain their own notices in their distributions. The following inventory was checked against installed distribution metadata (`License-Expression`, `License`, classifiers and the referenced license files) during release validation. Versions identify the audited environment, not a requirement to use that exact version on every supported Python release.

| Distribution | Audited version | License |
| --- | --- | --- |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| attrs | 26.1.0 | MIT |
| beautifulsoup4 | 4.15.0 | MIT License |
| certifi | 2026.10.23 | MPL-2.0 |
| cffi | 2.1.1 | MIT-0 |
| charset-normalizer | 3.5.2 | MIT |
| click | 8.5.0 | BSD-3-Clause |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| curl_cffi | 0.16.3 | MIT |
| h11 | 0.16.0 | MIT |
| httpcore | 1.0.9 | BSD-3-Clause |
| httpx | 0.28.1 | BSD-3-Clause |
| httpx-sse | 0.4.3 | MIT |
| idna | 3.20 | BSD-3-Clause |
| jsonschema | 4.26.0 | MIT |
| jsonschema-specifications | 2025.9.1 | MIT |
| lxml | 6.1.3 | BSD-3-Clause |
| mcp | 1.30.0 | MIT |
| multitasking | 0.0.13 | Apache-2.0 (installed LICENSE.txt) |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| pandas | 3.1.0 | BSD-3-Clause |
| peewee | 4.5.3 | MIT (installed LICENSE file) |
| platformdirs | 4.13.5 | MIT |
| protobuf | 7.36.2 | 3-Clause BSD License |
| pycparser | 3.12 | BSD-3-Clause |
| pydantic | 2.14.1 | MIT |
| pydantic-settings | 2.16.1 | MIT |
| pydantic_core | 2.50.1 | MIT |
| PyJWT | 2.15.1 | MIT |
| pypdf | 6.19.0 | BSD-3-Clause |
| python-dateutil | 3.0.0 | Apache-2.0 OR BSD-3-Clause (installed LICENSE) |
| python-dotenv | 1.2.4 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| pytz | 2026.5 | MIT |
| referencing | 0.37.0 | MIT |
| requests | 2.34.2 | Apache-2.0 |
| rpds-py | 2026.9.1 | MIT |
| six | 1.17.0 | MIT |
| soupsieve | 3.0.4 | MIT |
| sse-starlette | 3.5.1 | BSD-3-Clause |
| starlette | 1.9.0 | BSD-3-Clause |
| typing-inspection | 0.4.4 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| tzdata | 2026.5 | Apache-2.0 |
| urllib3 | 2.8.0 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause |
| websockets | 17.3 | BSD-3-Clause |
| yfinance | 1.7.0 | Apache-2.0 |

Some binary wheels include separately licensed components; their complete bundled notices remain in the installed packages. Provider data is governed separately from these software licenses. In particular, yfinance is Apache-2.0 software accessing unofficial Yahoo data; its software license does not grant rights to redistribute that data.
