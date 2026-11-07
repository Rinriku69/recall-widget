# Linux / Docker facts I keep forgetting

<!--
Format: each "## ..." heading = 1 fact
  - The "## " line = the question (the widget shows it first)
  - Text under the heading up to the next "## " = the answer
  - `backticks` are shown in the code font
Save the file and the widget reloads it automatically
-->

## What are `rm -r` and `rm -f`
`-r` = recursive: can delete folders, removing everything inside (without `-r`, `rm` refuses to delete a folder)
`-f` = force: no confirmation prompt, and no error if the file doesn't exist
`-rf` is the two combined

## `rm -rf dir/*` vs `rm -rf dir/`
`dir/*` deletes the contents; the folder `dir` itself stays (empty)
`dir/` deletes the whole folder
Because the shell expands `*` into a list of files before `rm` sees it, and `dir` itself isn't in that list

## Who expands the `*` in `rm dir/*`
The shell (bash/sh), not `rm`
The shell expands `*` into a list of files before passing them to the command
`*` doesn't match files starting with a dot, like `.env`

## Why is `rm -rf` dangerous
No prompt, no trash bin. A wrong path or one stray space deletes the wrong thing
Inside a Dockerfile `RUN` it's fine, because it only affects the image being built

## image vs container
image = a template, read-only, e.g. `nginx:stable-alpine`
container = the thing actually running, created fresh from an image on every `docker run`

## What does `docker run --rm` do
Removes the container automatically when its process ends
Without it = the container stays around in Exited state (see it with `docker ps -a`, remove it with `docker container prune`)
`--rm` doesn't remove the image

## What does `docker run nginx:stable-alpine cat /etc/nginx/nginx.conf` do
Words after the image name override the image's `CMD`
So it runs `cat` instead of starting nginx, and the container stops when `cat` finishes
Handy for peeking at a file inside an image (add `--rm` so it doesn't linger)

## Does `RUN rm` in a later layer make the image smaller
No. The file still exists in the earlier layer, it's just hidden
To actually shrink the image, delete it in the same `RUN` line that created the file

## `WORKDIR` in a Dockerfile vs `RUN cd`
`WORKDIR` sets the current folder for every following line (creating it if missing). `/app` is the usual choice
`RUN cd` only affects that one line, because each `RUN` runs in a new shell

## multi-stage: do `WORKDIR` or files from the first stage carry over to the next
No. Every `FROM` starts fresh from its base image's filesystem (`WORKDIR`, `ENV`, files, programs: all gone)
The only way across is `COPY --from=<stage name>`, which takes just the paths you name
That's why the final image has no `node_modules` or node binary

## Where is the source path of `COPY --from=build` relative to
To `/` of the source stage, not to its `WORKDIR`
If the first stage set `WORKDIR /app` → you must write `COPY --from=build /app/dist/web/browser/ ...`
The destination is relative to the current stage's `WORKDIR` (write a full path and you don't have to think about it)

## Are layer caches of different stages related
The cache store is shared, but each stage has its own chain of layers
When a line changes, that line and every later line in the same stage re-run
Stages only connect through `COPY --from`: if `dist` changes, that line in the nginx stage is redone too

## Does `COPY dist/app/browser /usr/share/nginx/html` give `html/browser/`
No. When the source is a folder, Docker copies its contents, not the folder itself
Result: `html/index.html`, not `html/browser/index.html`
A trailing `/` on `html/` or not makes no difference

## Does Docker `COPY` delete what's already in the destination folder
No, it merges: files with the same name are overwritten, others stay
e.g. nginx's `index.html` gets overwritten but `50x.html` is left behind
For a clean folder: `RUN rm -rf /usr/share/nginx/html/*` before `COPY`

## When does a trailing `/` on the `COPY` destination matter
When the source is a file
`COPY nginx.conf /etc/nginx/conf.d/` → gives `conf.d/nginx.conf`
`COPY nginx.conf /etc/nginx/site.conf` → gives a file named `site.conf` (renamed on the way)
If you mean the destination to be a folder, always end it with `/`

## Linux `cp -r` vs Docker `COPY`
`cp -r browser html` (with `html` already existing) → gives `html/browser/`, copying the folder itself
A trailing `/` on the source (`browser/`) still gives the same result
To copy only the contents: `cp -r browser/. html/`
Docker `COPY` always copies the contents

## What do a Dockerfile and `docker build` produce
Only an image. They don't run a container
A container comes later with `docker run` (or `docker compose up`), created from that image
So in a Dockerfile only `RUN` executes at build time; `CMD` is just a note about what to run at start

## When do `RUN` and `CMD` in a Dockerfile run
`RUN` = when building the image (`docker build`). The files it changes are saved as a layer
`CMD` = when the container starts (`docker run`). It doesn't run at build time; it's only recorded in metadata as the start command

## What happens if you write `RUN nginx -g "daemon off;"`
`docker build` hangs forever, because `RUN` waits for the command to finish and a server is designed never to finish
Even if it did finish, it'd be pointless: an image stores files, not running processes

## Why write `CMD` as an array `["nginx", "-g", "daemon off;"]`
Array (exec form): runs `nginx` directly as PID 1, so it receives `SIGTERM` from `docker stop` and shuts down cleanly
String `CMD nginx -g "daemon off;"` (shell form): runs through `/bin/sh -c`. `sh` becomes PID 1 and doesn't forward the signal, so `docker stop` waits 10 s and then kills it

## Why `daemon off;` in nginx's `CMD`
Keeps nginx running in the foreground instead of detaching into the background
A container lives as long as PID 1. If nginx went to the background, the main process would exit immediately and the container would stop

## What if a Dockerfile has several `CMD` lines
Only the last one counts
And `CMD` is just a default: words after the image name in `docker run` override it

## Can array-form `CMD` use `$VAR` or `&&`
No, because there's no shell to interpret them
If you need them, write `["sh", "-c", "..."]` (but then `sh` becomes PID 1 instead)

## Who owns the `;` at the end of `"daemon off;"`
nginx. Every directive must end with `;`, just like in `nginx.conf`
It has nothing to do with the shell

## What is nginx `default_server`, and which file is it in
It's not in any file. It's a parameter of `listen` you add yourself, e.g. `listen 80 default_server;`
The config shipped with the nginx image doesn't have this line at all
Docs: nginx.org, "How nginx processes a request"

## Which `server` block does nginx pick for a request on port 80
1. Compare the `Host` header with `server_name` of every server listening on that port. A match wins
2. No match → use the one marked `default_server`
3. No `default_server` → use the first server in config read order (`include conf.d/*.conf` reads files sorted by name)

## Does nginx inside an app container need `server_name`
With a single server block, anything works: when Host doesn't match it falls back to the first, which is the only one
But the nginx image ships `conf.d/default.conf`, so you must `COPY` over that exact name
Use a different name and you have two; file-name order decides, e.g. `web.conf` loses to `default.conf` and you get the "Welcome to nginx" page

## How does nginx `root` find a file
It joins `root` + the request path
`root /usr/share/nginx/html;` and a request for `/data/draws.json` → reads `/usr/share/nginx/html/data/draws.json`

## What does nginx `index` do
When the request is for a folder (path ends in `/`), it looks for files named in `index` inside that folder
`index index.html;` and a request for `/` → serves `/usr/share/nginx/html/index.html`

## How does nginx choose a `location` block
Pass 1, prefix: find the longest matching one, regardless of file order, and remember it
Pass 2, regex (`~`, `~*`): checked in file order; the first match immediately beats the remembered prefix
No regex matches → use the remembered prefix

## nginx `location =` and `location ^~` vs a plain prefix
`= /path` exact match; wins immediately, no regex pass
`^~ /path` is a prefix that says "if I'm the longest, regex may not override me", skipping the regex pass

## Does nginx `location /` catch every request first
No. It's the shortest possible prefix (one character), so it does match every request
But it always loses to longer prefixes and to every matching regex
It's "the default when nothing more specific matches", not a front door every request passes through

## Why does nginx ignore file order for prefixes but not for regex
Prefixes are stored in a tree sorted alphabetically, so the longest is found quickly without scanning one by one; order doesn't matter
Regexes are slower and can overlap, so they're checked in file order

## nginx has `location /`, `/data/`, `~* index\.html$`. Which block gets `/index.html`
`~* index\.html$`
Pass 1: the only matching prefix is `/` → remembered
Pass 2: regex `index\.html$` matches → wins

## `try_files $uri $uri/ /index.html` falls back to `/index.html`. Same location?
No. The last item of `try_files` is an internal redirect; nginx picks a location all over again
e.g. a request for `/special` → no file → goes to `/index.html` → lands in the `~* index\.html$` block instead

## nginx: what's the trap with a top-level regex `~* \.js$` and `location /data/`
Request `/data/x.js`: pass 1 gives `/data/`, but in pass 2 the regex `\.js$` matches → regex wins
So files under `/data/` get the 1-year cache meant for hashed files, instead of the intended `no-cache`
It doesn't break yet if `/data/` has no file matching the regex, but it breaks silently the day someone adds one
Fix: nest the regex inside `location / { ... }` (only checked when `/` is the winning prefix), or use `location ^~ /data/`

## How to check which nginx location block a request hits
Add a different header in each block, e.g. `add_header X-Hit "prefix-data" always;`
Then `curl -I http://localhost:8080/data/x.js` and look at `X-Hit`

## regex: `.` vs `\.`
`.` = any single character: `a.c` matches `abc`, `a-c`, `a.c`
`\.` = a literal dot (`\` cancels the special meaning): `\.js` matches only `.js`

## regex: what are `^` and `$`
`^` = text starts here: `^/data/` = starts with `/data/`
`$` = text ends here: `\.js$` = ends with `.js`

## regex: what do parentheses `(...)` do
1. Grouping: set the scope of `|`
2. Capturing: save the matched text as `$1`, `$2`, ... for later use
`(?:...)` = does only job 1, no capturing. Called a non-capturing group

## regex: `(js|css)` vs `(?:js|css)`
They match the same; the only difference is `(...)` captures into `$1` and `(?:...)` doesn't
If nothing uses `$1`, both give the same result. `?:` just tells the reader it's only for grouping, and is a tiny bit faster (barely measurable)

## Why must `\.js|css$` be written with parentheses as `\.(?:js|css)$`
Without parentheses, `|` splits the whole regex into two sides
`\.js|css$` = contains `.js` anywhere, OR ends with `css` (so `/a.json` matches, since it contains `.js`)
Parentheses limit `|` to choosing only within them

## regex: how is `$1` counted when `(?:...)` is mixed in
Only plain `(...)` groups count; `(?:...)` doesn't
`^/users/(\d+)/(\w+)$` on `/users/42/posts` → `$1` = `42`, `$2` = `posts`
`^/users/(?:\d+)/(\w+)$` on `/users/42/posts` → `$1` = `posts`

## regex: what are `\d` and `\w`
`\d` = 1 digit (same as `[0-9]`)
`\w` = 1 letter, digit, or `_` (same as `[A-Za-z0-9_]`)
`\d+` = one or more digits in a row, e.g. `42`

## How does nginx use `$1` from a `location` regex
`location ~ ^/users/(\d+)$ { return 200 "user id = $1"; }`
Request `/users/42` → returns `user id = 42`

## regex: when do you need parentheses
There's a `|` → wrap the alternatives in parentheses. Use `(?:...)` if you don't need `$1`
Only one option → no parentheses needed, e.g. `(index\.html)$` can be just `index\.html$`
You'll use `$1` later → use plain `(...)`

## regex: what does `?` after a character mean
The preceding item is optional
`jpe?g` matches `jpg` and `jpeg`

## regex: what are `[A-Z0-9]`, `+`, `*`, `{8}`
`[A-Z0-9]` = 1 character within this range
`+` / `*` / `{8}` = the preceding item 1+ times / 0+ times / exactly 8 times
`[A-Z0-9]{8}` = 8 uppercase letters or digits

## `*` in regex vs `*` in the shell
shell (glob): `*` = anything, any length, e.g. `rm dir/*`
regex: `*` = repeat the preceding item 0+ times; it can't stand alone
For "anything" in regex, write `.*`

## How do you read the regex `\.(?:js|css|woff2?)$`
Ends with `.js`, `.css`, `.woff`, or `.woff2`
`\.` a literal dot, `(?:...|...)` one of these, `2?` an optional 2, `$` ends here

## What is an exit code
Every command returns a number to the shell when it finishes: `0` = success, non-`0` = failure
See the last command's with `echo $?` (PowerShell: `$LASTEXITCODE`)
CI (GitHub Actions) uses it to mark a step ✅/❌, e.g. `ng test` with a failing test → non-0 exit code → the job stops

## YAML: what does indentation level mean
Indentation = structure (like `{ }` in JSON). Tabs aren't allowed
Keys at the same indentation are siblings; deeper indentation means children
A weird error like `Unexpected value 'run'` usually means a key is at the wrong level. Picture what the JSON structure would be

## What is `~` in a path
The home directory of the user running the command. The shell expands it before the command sees it
On a GitHub runner `~/.npm` = `/home/runner/.npm`
root uses `/root`; regular users use `/home/<username>`

## Where are relative paths in GitHub Actions relative to
`$GITHUB_WORKSPACE`, the folder `actions/checkout` cloned the repo into
`cache-dependency-path: web/package-lock.json` → GitHub prefixes it to `$GITHUB_WORKSPACE/web/package-lock.json`, so no full path needed
e.g. `/home/runner/work/mui-lotto/mui-lotto`. If you need the full path, use `${{ github.workspace }}`; don't hard-code it

## GitHub Actions: what is `${{ ... }}`
An expression GitHub evaluates before running the step, substituting the value into the text
Used to read values from contexts like `github`, `secrets`, `steps`

## GitHub Actions: what do the `github`, `secrets`, `steps` contexts give you
`github.actor`, `github.repository`, `github.sha` = event info: who pushed, which repo, which commit
`secrets.GITHUB_TOKEN` = tokens / secret values
`steps.<id>.outputs.<name>` = values output by an earlier step

## GitHub Actions: commonly used values in the `github` context
`github.actor` = who triggered this run (pushed, opened the PR, clicked merge)
`github.repository` = `owner/repo-name`
`github.event_name` = the triggering event, e.g. `push`, `pull_request`
`github.ref` = branch/ref, e.g. `refs/heads/main`
`github.sha` = the commit being run
`github.event` = the whole webhook payload (PR number, commit message, etc.)

## GitHub Actions: what is `github.ref` when running from a PR
Not the branch name, but `refs/pull/<PR number>/merge` (a simulated commit with the PR merged into the base)
GitHub tests this temporary merge commit, not the branch itself, so PR tests check the post-merge result before you actually merge
That's why `if: github.ref == 'refs/heads/main'` stops a deploy job from running on PRs
The PR's branch name is in `github.head_ref`

## GitHub Actions: when does the `pull_request` trigger run
By default in 3 cases: `opened` (PR opened), `synchronize` (new commit pushed to the PR branch), `reopened` (a closed PR reopened)
It doesn't run on merge
(To run when a PR closes, add `types: [closed]` yourself)

## GitHub Actions: which event triggers the workflow when you merge a PR
`push` to main, because merging creates a new commit on main
Open a PR / push more → `pull_request` → test ✅ deploy ⏭
Click merge → `push` (main) → test ✅ deploy ✅

## GitHub Actions: why does the deploy job need `if:` when `on:` is already set
`on:` is at the workflow level, not per job
A workflow triggered by `pull_request` runs every job, including deploy
So the deploy job needs its own `if:` guard

## GitHub Actions: `${{ github.sha }}` vs `$GITHUB_SHA`
Same value, different substitutor
`${{ }}` = GitHub substitutes it into the script before the shell sees it
`$GITHUB_SHA` = an env var the shell reads itself at run time (like `$HOME`)

## GitHub Actions: what's needed before `steps.<id>.outputs` works
The source step must have an `id:` and write its output to the `$GITHUB_OUTPUT` file
e.g. `echo "tag=v1" >> "$GITHUB_OUTPUT"` in a step with `id: meta`
Later steps read it with `${{ steps.meta.outputs.tag }}`

## "Last login: ... from <IP>" when you SSH in: what is it
The previous login, not this one
Most home/mobile IPs change (dynamic IP), so you can see a different IP even when it was you

## Seeing who has logged into the machine
`echo $SSH_CLIENT` = the IP of the current session (you, right now)
`who` = who is logged in right now
`last -i` = history of successful logins (who, which IP, when)
`sudo grep "Accepted" /var/log/auth.log` = successful logins, with the method (password / publickey)

## auth.log full of "Failed password": have I been hacked
No. Those are bots guessing passwords against every IP on the internet; a new machine gets hit within minutes
What to worry about is `Accepted` lines from IPs you don't recognize
Prevention: SSH keys only, disable `PasswordAuthentication`

## How to enable `ufw` without locking yourself out
Always `sudo ufw allow OpenSSH` before `sudo ufw enable`
Otherwise the firewall cuts SSH immediately and you can't get back in (recovery is through the VPS provider's web console)
After enabling, test in a new SSH window before closing the old one

## What are `ufw default deny incoming` / `allow outgoing`
The defaults when no rule matches: all incoming blocked, all outgoing allowed
Then `allow` only the ports you need (a whitelist)

## Docker `ports:` bypasses `ufw`
Docker writes its own iptables rules that run before ufw's. A port published with `-p 8080:80` is open to the internet even if ufw doesn't allow it
To allow access only from the machine itself, use `-p 127.0.0.1:8080:80`
Containers that don't publish ports (talking over a docker network) don't have this problem

## sshd reads a setting twice: which value wins
The first one found wins (unlike nginx or CSS, where later overrides earlier)
`/etc/ssh/sshd_config` has `Include /etc/ssh/sshd_config.d/*.conf` near the top, so files in `.d/` are read first
Name your file starting with `00-` so it's read before others, e.g. `50-cloud-init.conf`

## Seeing the sshd settings actually in effect
`sudo sshd -t` = check syntax (no output = OK)
`sudo sshd -T` = print every setting after merging all files, e.g. `sudo sshd -T | grep -i passwordauth`

## Testing that password login is really disabled
`ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password user@host`
You should get `Permission denied (publickey)` immediately, without a password prompt

## `grep: ...: Permission denied` even though the file exists
Your user isn't allowed to read that file (e.g. root's `600` file). Use `sudo grep ...`
Check permissions with `ls -l`, e.g. `-rw------- root root` = only root can read/write
Config files that may contain secrets are often set like this

## Seeing which program holds a port
`sudo ss -tlnp` = listening TCP ports with process names
`-t` TCP, `-l` listening, `-n` numeric ports (don't resolve to names), `-p` show process (needs sudo)
`127.0.0.1:8080` = accepts only from this machine, `0.0.0.0:80` = accepts from anywhere
`sudo ss -tlnp | grep 8081` = keep only lines containing `8081`. No output = nothing listens on that port

## Commonly used `curl` flags
`-I` = headers only (sends `HEAD`, not `GET`)
`-v` = show everything, request and response headers; `-s` = silent, no progress
`-H "Name: value"` = add a header to the request; `-L` = follow redirects
`-o /dev/null` = discard the body; `-D -` = print response headers to the screen (`-` = stdout)

## Checking with `curl` whether a response is gzipped
`curl -s -o /dev/null -D - -H "Accept-Encoding: gzip" <URL>` and look for `Content-Encoding: gzip`
You must add `Accept-Encoding` yourself, because curl doesn't tell the server it accepts gzip (browsers always do)
Use `GET` like this instead of `-I`, because `HEAD` may return headers that differ from a real request
`--http1.0` / `--http1.1` = force an HTTP version, useful for comparing

## What is an SSH host key fingerprint
A fingerprint of the server machine's own public key, used to verify you're connecting to the real machine
On the server: `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`
What your machine remembers: `ssh-keygen -lF <IP>` (reads `~/.ssh/known_hosts`)

## What each flag in `ssh-keygen -lf <file>` means
`-l` = list: show the key's fingerprint
`-f <file>` = which key file (`-f -` = read from stdin, e.g. piped from `ssh-keyscan`)
Careful: capital `-F` = find: look up a host in `known_hosts`, a different meaning from `-f`

## Host key vs the key you log in with
host key (`/etc/ssh/ssh_host_*_key.pub`) = belongs to the server; `sshd` uses it to prove "I'm the real machine"
login key (`~/.ssh/id_ed25519`) = belongs to a person; proves "I'm this user"
They prove opposite directions: the host key stops you connecting to the wrong machine; the login key replaces a password

## nginx on Ubuntu: `sites-available` vs `sites-enabled`
`sites-available/` = holds every site's config; `sites-enabled/` = symlinks to the active ones
nginx reads only `sites-enabled/`. Enable a site: `sudo ln -s /etc/nginx/sites-available/x /etc/nginx/sites-enabled/`
Disable a site: delete the symlink (the original file stays)

## `systemctl reload` vs `restart`
`reload` = re-read config without dropping existing connections (nginx supports it)
`restart` = stop and start again; the site is briefly down
Use `sudo nginx -t && sudo systemctl reload nginx` so the reload only happens when the config passes

## What does nginx `gzip on` alone compress
Only `text/html`
Other types (json, js, css) must be listed in `gzip_types`, e.g. `gzip_types application/json application/javascript text/css;`

## Which HTTP version does nginx `proxy_pass` forward with
`HTTP/1.0` by default, even if the browser sent 1.1
Fix with `proxy_http_version 1.1;` in the block that has `proxy_pass`

## Two layers of nginx (proxy → container) and `draws.json` isn't gzipped. Why
The outer layer forwards as `HTTP/1.0` (the `proxy_pass` default)
The inner layer defaults to `gzip_http_version 1.1` = no gzip for 1.0 requests, so it returns the raw file
The outer layer has `gzip on` but no `gzip_types`, so it only compresses HTML. In the end, the JSON isn't compressed by either layer
Fix: `proxy_http_version 1.1;` on the outer layer. Proof: `curl` straight into the container with `--http1.0` vs `--http1.1`

## `cmd1 && cmd2` vs `cmd1; cmd2`
`&&` = run `cmd2` only if `cmd1` succeeded (exit code 0)
`;` = always run `cmd2`, regardless of `cmd1`'s result

## What is `|` (pipe)
Takes what the left command prints and feeds it as input (stdin) to the right command, instead of showing it on screen
`echo "$TOKEN" | docker login ... --password-stdin` = sends the token into `docker login`'s stdin
`ss -tlnp | grep 8081` = sends `ss`'s output to `grep` to filter

## Why write `"$TOKEN"` with quotes
So the shell passes the value as one piece
No quotes + a value with spaces or special characters → the shell splits it into several pieces, or expands `*`
Good habit: always wrap variables in `"..."`

## `IMAGE_TAG=sha-bbb docker compose up -d` (a variable before the command): what is it
Sets an env var for that one command only; it's gone afterward and doesn't stay in the shell
Unlike `export IMAGE_TAG=...`, which stays for every following command

## What is `set -e` in a shell script
`set` = a shell command that turns the shell's own options on/off; `-e` = exit on error
If any command fails (non-0 exit code), the script stops immediately
Without it = it breaks midway but keeps going, and the script's exit code = the last command's (it may look like success)
In `appleboy/ssh-action`, use it instead of the removed `script_stop` option: without it, `pull` fails but the step shows green

## What is `set -x`
Prints every command before running it (prefixed with `+`). Used when debugging to see how far the script got and what the variables were
Careful: secret values in commands will show up in the log too

## What is `trap 'command' EXIT`
Registers a command to run when the script ends, whether it succeeded or failed
Used for cleanup, e.g. `trap 'docker logout ghcr.io' EXIT` paired with `set -e`
Why not put `docker logout` at the end of the script: if `set -e` stops it midway, the last line never runs, but `trap` runs in every case
JS comparison: similar to `finally { }`

## Why `docker login --password-stdin` instead of `-p`
`-p $TOKEN` makes the token part of the command, visible in `ps` and shell history
`echo "$TOKEN" | docker login ... --password-stdin` passes it through stdin, so it never appears in the command

## Deploying with `docker compose pull` then `docker compose up -d`: what does each do
`pull` = download the image for the tag in `compose.yml` (e.g. `:${IMAGE_TAG}`) onto the machine. Containers aren't touched yet
`up -d` = compose sees the image changed, so it recreates the container itself and runs it in the background (`-d` = detached)
No need to `down` first. Services whose image didn't change aren't touched

## Checking which image a container is running from
`docker inspect --format '{{.Config.Image}}' mui-lotto` → e.g. `ghcr.io/.../mui-lotto:sha-ea8f6aa`
Used to confirm the deploy really picked up the new sha
The `{{ }}` here is Docker's Go template, unrelated to GitHub Actions' `${{ }}`
Wrapped in `'...'` so the shell passes it through untouched

## Image on the VPS vs on GHCR: which is the real one
GHCR = permanent storage; every version ever pushed is still there (nothing is deleted unless you say so)
VPS = just a copy pulled for use; `prune` only deletes the copy
Old images gone from the VPS can still be rolled back to, because they can be pulled from GHCR again

## Rolling back by hand on the VPS
`cd` to the folder with `compose.yml`, then `IMAGE_TAG=sha-<old> docker compose up -d`
If that image isn't on the machine → compose pulls it from the registry itself, then creates a new container
A private image needs `docker login` first, then `logout` when done

## Rolling back through GitHub Actions (no SSH)
Open an old run of a known-good commit in the Actions tab → Re-run all jobs
The workflow checks out the old commit, builds (fast thanks to the cache), then deploys that commit's `sha-` tag
Careful: the `latest` tag also gets moved back to the old one

## You rolled back. Why isn't it over
Every kind of rollback is a temporary fix. The next push to main deploys the latest (still broken) code again
Permanent fix: `git revert <bad commit>` and push, so main is back to good code, then let the workflow deploy as usual

## `docker image prune -f` vs `-af`
`-f` = removes only dangling images (ones with no tag left)
`-af` = removes every image not used by a container (including tagged ones)
Limit the scope with `--filter "label=..."` so you don't delete other projects' images

## Why `docker image prune -f` isn't enough when every deploy tags the image with a sha
Old images still have their own tags (`sha-aaa`, `sha-bbb`, ...), so they aren't dangling
With `-f` alone, images pile up on every deploy. You need `-a`
Running containers are safe, because `-a` only removes images no container uses
Side effect: rolling back to an old sha has to `pull` from the registry again, since it's no longer on the machine

## How to filter `docker image prune -af` to one repo's images
`docker/metadata-action` adds the label `org.opencontainers.image.source` (the repo URL) to every image
`docker image prune -af --filter "label=org.opencontainers.image.source=https://github.com/<owner>/<repo>"`
Images from other projects on the same machine don't have this label, so they aren't removed

## Why "host key mismatch" when the fingerprint is correct
A server has several host key types (ED25519, ECDSA, RSA), each with a different fingerprint
Client and server negotiate which type to use: OpenSSH prefers ED25519, but Go's SSH library (used by appleboy/drone-ssh) prefers ECDSA
See all types from outside: `ssh-keyscan <host> | ssh-keygen -lf -`

## After editing a GitHub Actions secret, do you need to push again
No. Secrets are read when the job starts, so just click Re-run failed jobs
You can't view a secret's old value, only overwrite it
Copying a private key in PowerShell: `Get-Content <file> -Raw | Set-Clipboard` (`-Raw` keeps all the line breaks)

## `env:` in an `appleboy/ssh-action` step: why can't the script on the VPS see the variables
`env:` sets env vars for the step on GitHub's runner (with `${{ }}` already evaluated)
appleboy's script runs on the VPS, a different machine; variables don't cross over on their own
List the ones to send in `envs: IMAGE_TAG,GHCR_TOKEN`
Mental model: `env:` = packing your bag on the runner; `envs:` = picking which items to carry to the VPS
