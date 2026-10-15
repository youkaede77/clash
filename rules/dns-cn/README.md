# CN DNS rule data

`cn.mrs` is extracted from the public KaringX/clashmi `assets/datas/geosite.zip` archive and recompressed with a Zstandard decoder window of at most 64 KiB. The decoded MRS bytes are verified identical; domain entries are not removed or substituted.

The existing daily update workflow refreshes this data along with the regional rules. `manifest.json` records source and output hashes. A client must use `behavior: domain`, `format: mrs`, and a nonzero refresh interval to receive updates.

This reduces the compression window, but does not establish an overall memory reduction or guarantee iOS VPN stability. No node subscriptions or client configurations are published here.
