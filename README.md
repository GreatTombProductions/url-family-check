# URL Family Check

The address you share can show a login while another address for the same project still answers. This is a one-page note of what Vercel, Netlify, and Cloudflare Pages say about that, plus a command you run on your own computer.

Nothing here logs in, follows a redirect, or keeps a list of your addresses.

## Run it

Put `check.py` next to you and pass the addresses from your project's deploy list:

```bash
python3 check.py https://app.example.com https://older-deployment.example
python3 check.py --file addresses.txt
```

`redirect` means the address answered with a redirect, which was not followed. `served` means it returned a page (the body is not read). `challenged` is 401, `refused` is 403. Anything else, including a failed request, is `other` — a failure is not protection.

The checks that ship with the command talk only to a server on your own machine:

```bash
python3 tests/test_check.py
```

The scope table on the page was read on 14 November 2026. It is not updated on its own.
