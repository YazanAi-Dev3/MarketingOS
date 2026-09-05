# Source Adapter Seed Knowledge

The legacy project contained platform-specific knowledge for Mostaql, Khamsat and Bahr: search URL behavior, pagination, selectors, listing/detail distinctions and available metadata. This is useful **seed knowledge only**.

Before implementing each adapter:
1. run `T-09` against the current public site;
2. document current listing/detail/search/pagination/JS behavior;
3. choose direct HTTP vs Crawl4AI strategy;
4. define deterministic extraction schema where stable;
5. preserve evidence/provenance;
6. add fixtures and a bounded live smoke check.

Historical selectors are not copied into production without revalidation.
