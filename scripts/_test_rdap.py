import asyncio, httpx, dns.asyncresolver

async def test():
    domain = "onelink.me"

    # 1. RDAP via rdap.org
    async with httpx.AsyncClient(follow_redirects=True) as c:
        r = await c.get(f"https://rdap.org/domain/{domain}", timeout=15)
        print(f"RDAP rdap.org: status={r.status_code}")
        if r.status_code == 200:
            d = r.json()
            statuses = d.get("status", [])
            print(f"  domain status: {statuses}")

    # 2. RDAP via IANA
    async with httpx.AsyncClient(follow_redirects=True) as c:
        r2 = await c.get(f"https://rdap.iana.org/domain/{domain}", timeout=15)
        print(f"RDAP iana: status={r2.status_code}")

    # 3. DNS check
    try:
        ans = await dns.asyncresolver.resolve(domain, "A")
        print(f"DNS A: {[str(r) for r in ans]}")
    except Exception as e:
        print(f"DNS A failed: {e}")

asyncio.run(test())
