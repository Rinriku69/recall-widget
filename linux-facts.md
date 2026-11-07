# Linux / Docker facts ที่ชอบลืม

<!--
รูปแบบ: หัวข้อ "## ..." แต่ละอัน = 1 fact
  - บรรทัด "## " = คำถาม (widget โชว์ก่อน)
  - ข้อความใต้หัวข้อจนถึง "## " ถัดไป = คำตอบ
  - ใส่ `backtick` ได้ widget จะแสดงเป็นฟอนต์ code
แก้ไฟล์แล้วเซฟ widget จะโหลดใหม่เอง
-->

## `rm -r` กับ `rm -f` คืออะไร
`-r` = recursive: ลบโฟลเดอร์ได้ ไล่ลบทุกอย่างข้างใน (ไม่ใส่ `-r` `rm` จะไม่ยอมลบโฟลเดอร์)
`-f` = force: ไม่ถามยืนยัน และไม่ error ถ้าไม่มีไฟล์
`-rf` คือสองตัวเขียนรวมกัน

## `rm -rf dir/*` กับ `rm -rf dir/` ต่างกันยังไง
`dir/*` ลบของข้างใน โฟลเดอร์ `dir` ยังอยู่ (ว่าง)
`dir/` ลบตัวโฟลเดอร์ทิ้งทั้งก้อน
เพราะ `*` ถูก shell ขยายเป็นรายชื่อไฟล์ก่อน `rm` จะเห็น ชื่อ `dir` เองไม่อยู่ในรายการ

## ใครเป็นคนแปลง `*` ใน `rm dir/*`
shell (bash/sh) ไม่ใช่ `rm`
shell ขยาย `*` เป็นรายชื่อไฟล์ก่อนส่งให้คำสั่ง
`*` ไม่จับไฟล์ที่ขึ้นต้นด้วยจุด เช่น `.env`

## ทำไม `rm -rf` อันตราย
ไม่ถาม ไม่มีถังขยะ path ผิดหรือมีช่องว่างเกินตัวเดียวก็ลบผิดที่
ใน `RUN` ของ Dockerfile ไม่เป็นไร เพราะกระทบแค่ image ที่กำลัง build

## image กับ container ต่างกันยังไง
image = แม่แบบ อ่านได้อย่างเดียว เช่น `nginx:stable-alpine`
container = ตัวที่รันจริง ถูกสร้างใหม่จาก image ทุกครั้งที่ `docker run`

## `docker run --rm` คืออะไร
ลบ container ทิ้งอัตโนมัติเมื่อ process จบ
ไม่ใส่ = container ค้างสถานะ Exited (ดูด้วย `docker ps -a`, ลบด้วย `docker container prune`)
`--rm` ไม่ลบ image

## `docker run nginx:stable-alpine cat /etc/nginx/nginx.conf` ทำอะไร
คำที่ต่อท้ายชื่อ image จะทับ `CMD` เดิมของ image
เลยรัน `cat` แทนการเปิด nginx พอ `cat` จบ container ก็หยุด
ใช้แอบดูไฟล์ใน image ได้ (ใส่ `--rm` ด้วยจะได้ไม่ค้าง)

## `RUN rm` ไฟล์ใน layer หลัง ทำให้ image เล็กลงไหม
ไม่ ไฟล์ยังอยู่ใน layer ก่อนหน้า แค่ถูกซ่อน
อยากให้เล็กจริงต้องลบในบรรทัด `RUN` เดียวกับที่สร้างไฟล์นั้น

## `WORKDIR` ใน Dockerfile ต่างจาก `RUN cd` ยังไง
`WORKDIR` ตั้งโฟลเดอร์ปัจจุบันให้ทุกบรรทัดถัดไป (สร้างให้ถ้ายังไม่มี) นิยมใช้ `/app`
`RUN cd` มีผลแค่บรรทัดนั้น เพราะ `RUN` แต่ละบรรทัดรันใน shell ใหม่

## multi-stage: `WORKDIR` หรือไฟล์ใน stage แรก ข้ามไป stage ถัดไปไหม
ไม่ข้าม ทุก `FROM` เริ่มจาก filesystem ของ base image ใหม่หมด (`WORKDIR`, `ENV`, ไฟล์, โปรแกรม หายหมด)
ทางเดียวที่ข้ามได้คือ `COPY --from=<ชื่อ stage>` ซึ่งหยิบมาเฉพาะ path ที่สั่ง
image สุดท้ายจึงไม่มี `node_modules` หรือตัว node ติดไป

## path ต้นทางของ `COPY --from=build` นับจากไหน
นับจาก `/` ของ stage ต้นทาง ไม่ใช่จาก `WORKDIR` ของมัน
stage แรกตั้ง `WORKDIR /app` ไว้ → ต้องเขียน `COPY --from=build /app/dist/web/browser/ ...`
ส่วนปลายทางนับจาก `WORKDIR` ของ stage ปัจจุบัน (เขียน path เต็มจะไม่ต้องคิด)

## layer cache ของแต่ละ stage เกี่ยวกันไหม
ที่เก็บ cache ใช้ร่วมกัน แต่แต่ละ stage มีสาย layer ของตัวเอง
บรรทัดไหนเปลี่ยน บรรทัดนั้นและทุกบรรทัดหลังจากนั้นใน stage เดียวกันรันใหม่
ข้าม stage เชื่อมกันแค่ผ่าน `COPY --from` ถ้า `dist` เปลี่ยน บรรทัดนั้นใน stage nginx ก็ทำใหม่ด้วย

## `COPY dist/app/browser /usr/share/nginx/html` ได้ `html/browser/` ไหม
ไม่ได้ เมื่อ source เป็นโฟลเดอร์ Docker copy ของข้างใน ไม่เอาตัวโฟลเดอร์ไปด้วย
ผลคือ `html/index.html` ไม่ใช่ `html/browser/index.html`
ใส่ `/` ท้ายเป็น `html/` หรือไม่ใส่ ผลก็เหมือนกัน

## Docker `COPY` ลบของเดิมในโฟลเดอร์ปลายทางไหม
ไม่ลบ แต่ merge: ไฟล์ชื่อซ้ำถูกทับ ไฟล์ที่ไม่ซ้ำยังอยู่
เช่น `index.html` ของ nginx ถูกทับ แต่ `50x.html` ยังค้าง
อยากให้สะอาด: `RUN rm -rf /usr/share/nginx/html/*` ก่อน `COPY`

## `/` ท้าย destination ของ `COPY` มีผลเมื่อไหร่
มีผลตอน source เป็นไฟล์
`COPY nginx.conf /etc/nginx/conf.d/` → ได้ `conf.d/nginx.conf`
`COPY nginx.conf /etc/nginx/site.conf` → ได้ไฟล์ชื่อ `site.conf` (เปลี่ยนชื่อไปในตัว)
ตั้งใจให้ปลายทางเป็นโฟลเดอร์ ใส่ `/` ปิดท้ายเสมอ

## `cp -r` ของ Linux ต่างจาก Docker `COPY` ยังไง
`cp -r browser html` (มี `html` อยู่แล้ว) → ได้ `html/browser/` คือ copy ตัวโฟลเดอร์ไปทั้งก้อน
`/` ท้าย source (`browser/`) ก็ยังได้แบบเดิม
อยากได้แค่ของข้างใน: `cp -r browser/. html/`
Docker `COPY` copy ของข้างในเสมอ

## Dockerfile กับ `docker build` มีไว้สร้างอะไร
สร้าง image อย่างเดียว ไม่ได้รัน container
container เกิดทีหลังตอน `docker run` (หรือ `docker compose up`) โดยสร้างจาก image นั้น
ใน Dockerfile จึงมีแค่ `RUN` ที่ทำงานตอน build ส่วน `CMD` เป็นแค่โน้ตว่าตอน run ให้ทำอะไร

## `RUN` กับ `CMD` ใน Dockerfile ทำงานตอนไหน
`RUN` = ตอน build image (`docker build`) ผลที่ได้คือไฟล์ที่เปลี่ยน ถูกบันทึกเป็น layer
`CMD` = ตอน start container (`docker run`) ตอน build ไม่ได้รัน แค่จดไว้ใน metadata ว่าให้รันคำสั่งนี้ตอน start

## ถ้าเขียน `RUN nginx -g "daemon off;"` จะเกิดอะไร
`docker build` ค้างตลอดไป เพราะ `RUN` รอคำสั่งจบก่อน แต่ server ถูกออกแบบมาให้ไม่จบ
ต่อให้จบได้ก็ไม่มีประโยชน์ image เก็บแค่ไฟล์ ไม่ได้เก็บ process ที่กำลังรัน

## ทำไม `CMD` ต้องเขียนเป็น array `["nginx", "-g", "daemon off;"]`
แบบ array (exec form): รัน `nginx` ตรงๆ เป็น PID 1 เลยได้รับสัญญาณ `SIGTERM` จาก `docker stop` แล้วปิดตัวอย่างเรียบร้อย
แบบ string `CMD nginx -g "daemon off;"` (shell form): รันผ่าน `/bin/sh -c` ตัว `sh` เป็น PID 1 และไม่ส่งสัญญาณต่อ `docker stop` เลยรอ 10 วิแล้ว kill ทิ้ง

## `daemon off;` ใน `CMD` ของ nginx มีไว้ทำไม
ให้ nginx รันค้างอยู่ด้านหน้า (foreground) ไม่แยกตัวไปทำงานเบื้องหลัง
container อยู่ได้นานเท่ากับ PID 1 ถ้า nginx แยกตัวไปเบื้องหลัง process หลักจะจบทันทีและ container ก็หยุดตาม

## Dockerfile มี `CMD` หลายบรรทัดจะเป็นยังไง
ใช้แค่บรรทัดสุดท้าย
และ `CMD` เป็นแค่ค่า default คำที่ต่อท้ายชื่อ image ตอน `docker run` จะทับมัน

## `CMD` แบบ array ใช้ `$VAR` หรือ `&&` ได้ไหม
ไม่ได้ เพราะไม่มี shell มาแปลงให้
ถ้าจำเป็นให้เขียน `["sh", "-c", "..."]` (แต่ `sh` จะกลายเป็น PID 1 แทน)

## `;` ท้าย `"daemon off;"` เป็นของใคร
ของ nginx ทุก directive ต้องปิดด้วย `;` เหมือนใน `nginx.conf`
ไม่เกี่ยวกับ shell

## nginx `default_server` คืออะไร อยู่ไฟล์ไหน
ไม่ได้อยู่ไฟล์ไหน เป็นพารามิเตอร์ของ `listen` ที่ต้องเขียนเพิ่มเอง เช่น `listen 80 default_server;`
config ที่มากับ image nginx ไม่มีบรรทัดนี้เลย
เอกสาร: nginx.org หน้า "How nginx processes a request"

## nginx เลือก `server` block ไหน เมื่อมี request เข้าพอร์ต 80
1. เอา header `Host` ไปเทียบกับ `server_name` ของทุก server ที่ listen พอร์ตนั้น ตรงตัวไหนใช้ตัวนั้น
2. ไม่ตรงเลย → ใช้ตัวที่มี `default_server`
3. ไม่มี `default_server` → ใช้ server ตัวแรกตามลำดับที่อ่าน config (`include conf.d/*.conf` อ่านไฟล์เรียงตามชื่อ)

## `server_name` ใน nginx ของ container แอป ต้องใส่ไหม
ใส่อะไรก็ได้ ถ้ามี server block เดียว เพราะ Host ไม่ตรงก็ตกไปใช้ตัวแรก ซึ่งก็คือตัวเดียวที่มี
แต่ image nginx มี `conf.d/default.conf` ติดมา ต้อง `COPY` ทับชื่อนั้น
ถ้าตั้งชื่ออื่นจะมีสองตัว ตัดสินด้วยลำดับชื่อไฟล์ เช่น `web.conf` แพ้ `default.conf` ได้หน้า Welcome to nginx

## nginx `root` หาไฟล์ยังไง
เอา `root` + path ของ request มาต่อกัน
`root /usr/share/nginx/html;` แล้วขอ `/data/draws.json` → อ่าน `/usr/share/nginx/html/data/draws.json`

## nginx `index` ทำอะไร
ถ้าขอเป็นโฟลเดอร์ (path ลงท้ายด้วย `/`) ให้ลองหาไฟล์ตามชื่อใน `index` ในโฟลเดอร์นั้น
`index index.html;` แล้วขอ `/` → ได้ `/usr/share/nginx/html/index.html`

## nginx เลือก `location` บล็อกไหน
รอบ 1 prefix: หาตัวที่ตรงยาวที่สุด ไม่สนลำดับในไฟล์ แล้วจำไว้
รอบ 2 regex (`~`, `~*`): ไล่ตามลำดับในไฟล์ ตัวแรกที่ตรงชนะ prefix ที่จำไว้ทันที
ไม่มี regex ตรงเลย → ใช้ prefix ที่จำไว้

## nginx `location =` กับ `location ^~` ต่างจาก prefix ธรรมดายังไง
`= /path` ตรงเป๊ะ ชนะทันทีตั้งแต่ต้น ไม่ต้องไปรอบ regex
`^~ /path` เป็น prefix ที่บอกว่า "ถ้าฉันยาวที่สุด ห้าม regex แย่ง" ข้ามรอบ regex ไปเลย

## nginx `location /` ดักทุก request ก่อนใช่ไหม
ไม่ใช่ มันคือ prefix ที่สั้นที่สุด (ตัวเดียว) เลยตรงทุก request ก็จริง
แต่แพ้ prefix ที่ยาวกว่าเสมอ และแพ้ regex ทุกตัวที่ตรง
คือ "ค่าเริ่มต้นเมื่อไม่มีตัวไหนเจาะจงกว่า" ไม่ใช่ประตูหน้าที่ทุก request ต้องผ่าน

## ทำไม nginx prefix ไม่สนลำดับในไฟล์ แต่ regex สน
prefix เก็บในต้นไม้เรียงตามตัวอักษร หาตัวที่ยาวที่สุดได้เร็วโดยไม่ต้องไล่ทีละตัว ผลเลยไม่ขึ้นกับลำดับ
regex ช้ากว่าและตรงทับซ้อนกันได้ จึงต้องไล่ตามลำดับในไฟล์

## nginx มี `location /`, `/data/`, `~* index\.html$` ขอ `/index.html` เข้าบล็อกไหน
`~* index\.html$`
รอบ 1 prefix ที่ตรงมีแค่ `/` → จำไว้
รอบ 2 regex `index\.html$` ตรง → ชนะ

## `try_files $uri $uri/ /index.html` แล้วตกไปที่ `/index.html` ใช้ location เดิมไหม
ไม่ ตัวสุดท้ายของ `try_files` เป็น internal redirect nginx เลือก location ใหม่ทั้งหมด
เช่นขอ `/special` → ไม่มีไฟล์ → ไป `/index.html` → เข้าบล็อก `~* index\.html$` แทน

## nginx: regex `~* \.js$` ระดับบนสุด กับ `location /data/` มีกับดักอะไร
ขอ `/data/x.js`: รอบ 1 ได้ `/data/` แต่รอบ 2 regex `\.js$` ตรง → regex ชนะ
ไฟล์ใต้ `/data/` เลยได้ cache 1 ปีแบบไฟล์ที่มี hash ทั้งที่ตั้งใจให้ `no-cache`
ตอนนี้ยังไม่พังถ้าใน `/data/` ยังไม่มีไฟล์ที่ตรงกับ regex แต่จะพังเงียบๆ วันที่มีคนเพิ่มไฟล์แบบนั้น
แก้: ย้าย regex ไปซ้อนใน `location / { ... }` (ถูกเช็คเฉพาะตอน `/` เป็น prefix ที่ชนะ) หรือใช้ `location ^~ /data/`

## เช็คยังไงว่า request เข้า nginx location บล็อกไหน
ใส่ header ต่างกันในแต่ละบล็อก เช่น `add_header X-Hit "prefix-data" always;`
แล้ว `curl -I http://localhost:8080/data/x.js` ดูค่า `X-Hit`

## regex: `.` กับ `\.` ต่างกันยังไง
`.` = ตัวอักษรอะไรก็ได้ 1 ตัว: `a.c` ตรงกับ `abc`, `a-c`, `a.c`
`\.` = จุดจริงๆ (`\` ยกเลิกความหมายพิเศษ): `\.js` ตรงกับ `.js` เท่านั้น

## regex: `^` กับ `$` คืออะไร
`^` = เริ่มข้อความตรงนี้: `^/data/` = ขึ้นต้นด้วย `/data/`
`$` = จบข้อความตรงนี้: `\.js$` = ลงท้ายด้วย `.js`

## regex: วงเล็บ `(...)` ทำหน้าที่อะไรบ้าง
1. จัดกลุ่ม (grouping): กำหนดขอบเขตของ `|`
2. จำค่า (capturing): เก็บข้อความที่ตรงไว้เป็น `$1`, `$2`, ... เอาไปใช้ต่อได้
`(?:...)` = ใช้แค่หน้าที่ 1 ไม่จำค่า เรียกว่า non-capturing group

## regex: `(js|css)` กับ `(?:js|css)` ต่างกันยังไง
match ได้ผลเหมือนกัน ต่างแค่ `(...)` จำค่าเป็น `$1` ส่วน `(?:...)` ไม่จำ
ถ้าไม่มีที่ไหนใช้ `$1` สองแบบนี้ให้ผลเหมือนกัน `?:` แค่บอกคนอ่านว่ามีไว้จัดกลุ่ม และเร็วขึ้นนิดเดียว (แทบวัดไม่ได้)

## ทำไม `\.js|css$` ต้องมีวงเล็บเป็น `\.(?:js|css)$`
`|` แบ่งทั้ง regex ออกเป็นสองฝั่ง ถ้าไม่มีวงเล็บ
`\.js|css$` = มี `.js` ตรงไหนก็ได้ หรือ ลงท้ายด้วย `css` (เช่น `/a.json` ก็ตรง เพราะมี `.js` อยู่ข้างใน)
วงเล็บจำกัดให้ `|` เลือกแค่ส่วนข้างในวงเล็บ

## regex: `$1` นับวงเล็บยังไง เมื่อมี `(?:...)` ปน
นับเฉพาะ `(...)` ธรรมดา `(?:...)` ไม่ถูกนับ
`^/users/(\d+)/(\w+)$` กับ `/users/42/posts` → `$1` = `42`, `$2` = `posts`
`^/users/(?:\d+)/(\w+)$` กับ `/users/42/posts` → `$1` = `posts`

## regex: `\d` กับ `\w` คืออะไร
`\d` = ตัวเลข 1 ตัว (เหมือน `[0-9]`)
`\w` = ตัวอักษร ตัวเลข หรือ `_` 1 ตัว (เหมือน `[A-Za-z0-9_]`)
`\d+` = ตัวเลขติดกันอย่างน้อย 1 ตัว เช่น `42`

## nginx เอา `$1` จาก regex ใน `location` ไปใช้ยังไง
`location ~ ^/users/(\d+)$ { return 200 "user id = $1"; }`
ขอ `/users/42` → ได้ `user id = 42`

## regex: เมื่อไหร่ต้องใส่วงเล็บ
มี `|` → ต้องมีวงเล็บครอบตัวเลือก ใช้ `(?:...)` ถ้าไม่ต้องการ `$1`
ตัวเลือกเดียว → ไม่ต้องมีวงเล็บ เช่น `(index\.html)$` ถอดเป็น `index\.html$` ได้
จะใช้ `$1` ต่อ → ใช้ `(...)` ธรรมดา

## regex: `?` หลังตัวอักษรแปลว่าอะไร
ตัวก่อนหน้ามีหรือไม่มีก็ได้
`jpe?g` ตรงกับ `jpg` และ `jpeg`

## regex: `[A-Z0-9]`, `+`, `*`, `{8}` คืออะไร
`[A-Z0-9]` = ตัวอักษร 1 ตัวที่อยู่ในช่วงนี้
`+` / `*` / `{8}` = ตัวก่อนหน้า 1+ ครั้ง / 0+ ครั้ง / 8 ครั้งพอดี
`[A-Z0-9]{8}` = ตัวพิมพ์ใหญ่หรือตัวเลข 8 ตัว

## `*` ใน regex กับ `*` ใน shell ต่างกันยังไง
shell (glob): `*` = อะไรก็ได้กี่ตัวก็ได้ เช่น `rm dir/*`
regex: `*` = ตัวก่อนหน้าซ้ำ 0+ ครั้ง ใช้เดี่ยวๆ ไม่ได้
อยากได้ "อะไรก็ได้" ใน regex ต้องเขียน `.*`

## อ่าน regex `\.(?:js|css|woff2?)$` ว่าอะไร
ลงท้ายด้วย `.js`, `.css`, `.woff` หรือ `.woff2`
`\.` จุดจริง, `(?:...|...)` อย่างใดอย่างหนึ่ง, `2?` มี 2 หรือไม่มีก็ได้, `$` จบตรงนี้

## exit code คืออะไร
ทุกคำสั่งจบแล้วคืนตัวเลขให้ shell: `0` = สำเร็จ, ไม่ใช่ `0` = ล้มเหลว
ดูของคำสั่งล่าสุดด้วย `echo $?` (PowerShell: `$LASTEXITCODE`)
CI (GitHub Actions) ใช้ตัวนี้ตัดสิน step ✅/❌ เช่น `ng test` มี test พัง → exit code ไม่ใช่ 0 → job หยุด

## YAML: ระดับการเยื้องคืออะไร
การเยื้อง = โครงสร้าง (เหมือน `{ }` ใน JSON) ห้ามใช้ tab
key ที่เยื้องเท่ากันคือพี่น้องกัน เยื้องลึกกว่าคือลูก
error แปลกๆ อย่าง `Unexpected value 'run'` มักแปลว่า key ไปอยู่ผิดชั้น ลองนึกว่าถ้าเป็น JSON จะได้โครงแบบไหน

## `~` ใน path คืออะไร
home directory ของ user ที่รันคำสั่งอยู่ shell แปลงให้ก่อนส่งให้คำสั่ง
บน GitHub runner `~/.npm` = `/home/runner/.npm`
root ใช้ `/root`, user ทั่วไปใช้ `/home/ชื่อuser`

## path แบบ relative ใน GitHub Actions นับจากไหน
นับจาก `$GITHUB_WORKSPACE` คือโฟลเดอร์ที่ `actions/checkout` clone repo ลงไป
`cache-dependency-path: web/package-lock.json` → GitHub ต่อข้างหน้าให้เป็น `$GITHUB_WORKSPACE/web/package-lock.json` เลยไม่ต้องเขียน path เต็ม
เช่น `/home/runner/work/mui-lotto/mui-lotto` ถ้าต้องการ path เต็มให้ใช้ `${{ github.workspace }}` อย่าพิมพ์ path ตายตัว

## GitHub Actions: `${{ ... }}` คืออะไร
expression ที่ GitHub คำนวณก่อนรัน step แล้วแทนค่าลงไปในข้อความ
ใช้ดึงค่าจาก context ต่างๆ เช่น `github`, `secrets`, `steps`

## GitHub Actions: context `github`, `secrets`, `steps` ให้อะไร
`github.actor`, `github.repository`, `github.sha` = ข้อมูล event: ใครเป็นคน push, repo ไหน, commit ไหน
`secrets.GITHUB_TOKEN` = token / ค่าลับ
`steps.<id>.outputs.<ชื่อ>` = ค่าที่ step ก่อนหน้าส่งออกมา

## GitHub Actions: ใน context `github` มีค่าอะไรที่ใช้บ่อย
`github.actor` = ใคร trigger รอบนี้ (คนที่ push, เปิด PR, กด merge)
`github.repository` = `owner/ชื่อrepo`
`github.event_name` = event ที่ trigger เช่น `push`, `pull_request`
`github.ref` = branch/ref เช่น `refs/heads/main`
`github.sha` = commit ที่รันอยู่
`github.event` = payload ของ webhook ทั้งก้อน (เลข PR, ข้อความ commit ฯลฯ)

## GitHub Actions: ตอนรันจาก PR `github.ref` เป็นอะไร
ไม่ใช่ชื่อ branch แต่เป็น `refs/pull/<เลข PR>/merge` (commit จำลองที่ merge PR เข้า base แล้ว)
GitHub ทดสอบ merge commit ชั่วคราวนี้ ไม่ใช่ branch ตรงๆ test ใน PR จึงตรวจผลหลัง merge ได้ก่อนกด merge จริง
เลยใช้ `if: github.ref == 'refs/heads/main'` กัน job deploy ไม่ให้รันจาก PR ได้
ชื่อ branch ของ PR ดูที่ `github.head_ref`

## GitHub Actions: trigger `pull_request` ทำงานตอนไหน
ค่าเริ่มต้น 3 กรณี: `opened` เปิด PR, `synchronize` push commit ใหม่เข้า branch ของ PR, `reopened` เปิด PR ที่ปิดไปแล้ว
ไม่รันตอน merge
(อยากให้รันตอนปิด PR ต้องเพิ่ม `types: [closed]` เอง)

## GitHub Actions: กด merge PR แล้ว workflow ถูก trigger ด้วย event อะไร
`push` เข้า main เพราะการ merge คือการสร้าง commit ใหม่บน main
เปิด PR / push เพิ่ม → `pull_request` → test ✅ deploy ⏭
กด merge → `push` (main) → test ✅ deploy ✅

## GitHub Actions: ทำไม job deploy ต้องมี `if:` ทั้งที่ตั้ง `on:` ไว้แล้ว
`on:` อยู่ระดับ workflow ไม่ได้แยกตาม job
workflow ที่ถูก trigger ด้วย `pull_request` จะรันทุก job รวมถึง deploy
ต้องใช้ `if:` ที่ job deploy กันเอง

## GitHub Actions: `${{ github.sha }}` กับ `$GITHUB_SHA` ต่างกันยังไง
ค่าเดียวกัน แต่คนแทนค่าต่างกัน
`${{ }}` = GitHub แทนลงไปในสคริปต์ก่อน shell จะเห็น
`$GITHUB_SHA` = env var ที่ shell อ่านเองตอนรัน (เหมือน `$HOME`)

## GitHub Actions: `steps.<id>.outputs` ต้องทำอะไรก่อนถึงใช้ได้
step ต้นทางต้องมี `id:` และเขียน output ลงไฟล์ `$GITHUB_OUTPUT`
เช่น `echo "tag=v1" >> "$GITHUB_OUTPUT"` ใน step ที่มี `id: meta`
step หลังจากนั้นอ่านด้วย `${{ steps.meta.outputs.tag }}`

## "Last login: ... from <IP>" ตอน SSH เข้าเครื่อง คืออะไร
คือ login ครั้งก่อนหน้า ไม่ใช่ครั้งนี้
IP บ้าน/มือถือส่วนใหญ่เปลี่ยนได้ (dynamic IP) เลยเห็นคนละ IP ได้แม้เป็นตัวเราเอง

## ดูว่าใคร login เข้าเครื่องบ้าง
`echo $SSH_CLIENT` = IP ของ session ปัจจุบัน (ตัวเราตอนนี้)
`who` = ใครกำลัง login อยู่ตอนนี้
`last -i` = ประวัติ login ที่สำเร็จ (ใคร, IP ไหน, เมื่อไร)
`sudo grep "Accepted" /var/log/auth.log` = login สำเร็จ พร้อมวิธี (password / publickey)

## "Failed password" เต็ม auth.log แปลว่าโดนเจาะไหม
ไม่ใช่ เป็นบอทที่สุ่มเดารหัสทุก IP บนอินเทอร์เน็ต เครื่องใหม่โดนภายในไม่กี่นาที
ตัวที่ต้องห่วงคือบรรทัด `Accepted` จาก IP ที่ไม่รู้จัก
ป้องกัน: ใช้ SSH key อย่างเดียว ปิด `PasswordAuthentication`

## เปิด `ufw` ยังไงไม่ให้ล็อกตัวเองออกจากเครื่อง
ต้อง `sudo ufw allow OpenSSH` ก่อน `sudo ufw enable` เสมอ
ไม่งั้น firewall ตัด SSH ทันทีแล้วเข้าเครื่องไม่ได้ (ต้องไปกู้ผ่าน web console ของผู้ให้บริการ VPS)
หลัง enable ให้เปิด SSH หน้าต่างใหม่ทดสอบก่อนปิดหน้าต่างเดิม

## `ufw default deny incoming` / `allow outgoing` คืออะไร
ค่าเริ่มต้นเมื่อไม่มีกฎไหนตรง: ขาเข้าปิดหมด ขาออกเปิดหมด
แล้วค่อย `allow` เฉพาะพอร์ตที่ต้องใช้ (whitelist)

## Docker `ports:` ข้าม `ufw` ได้
Docker เขียนกฎ iptables เองก่อนถึงกฎของ ufw พอร์ตที่ publish ด้วย `-p 8080:80` เปิดสู่อินเทอร์เน็ตแม้ ufw ไม่ allow
ถ้าต้องการให้เข้าได้แค่ในเครื่อง ใช้ `-p 127.0.0.1:8080:80`
container ที่ไม่ publish port (คุยกันผ่าน docker network) ไม่โดนปัญหานี้

## sshd อ่าน config ซ้ำกันแล้วเชื่อค่าไหน
ค่าแรกที่เจอชนะ (ต่างจาก nginx หรือ CSS ที่ตัวหลังทับตัวหน้า)
`/etc/ssh/sshd_config` มี `Include /etc/ssh/sshd_config.d/*.conf` อยู่บรรทัดบนๆ ไฟล์ใน `.d/` จึงถูกอ่านก่อน
ตั้งชื่อไฟล์ให้ขึ้นต้นด้วย `00-` เพื่อให้ถูกอ่านก่อนไฟล์อื่น เช่น `50-cloud-init.conf`

## ดูค่า sshd ที่ใช้งานจริง
`sudo sshd -t` = ตรวจ syntax (ไม่มี output = ผ่าน)
`sudo sshd -T` = พิมพ์ค่าทั้งหมดหลังรวมทุกไฟล์แล้ว เช่น `sudo sshd -T | grep -i passwordauth`

## ทดสอบว่าปิด password login แล้วจริง
`ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password user@host`
ต้องได้ `Permission denied (publickey)` ทันที โดยไม่ถามรหัส

## `grep: ...: Permission denied` ทั้งที่ไฟล์มีอยู่
user เราไม่มีสิทธิ์อ่านไฟล์นั้น (เช่นไฟล์ที่เป็น `600` ของ root) ต้องใช้ `sudo grep ...`
ดูสิทธิ์ด้วย `ls -l` เช่น `-rw------- root root` = root อ่าน/เขียนได้คนเดียว
ไฟล์ config ที่อาจมีข้อมูลลับมักถูกตั้งแบบนี้

## ดูว่าโปรแกรมไหนจองพอร์ตอยู่
`sudo ss -tlnp` = พอร์ต TCP ที่กำลัง listen พร้อมชื่อ process
`-t` TCP, `-l` listening, `-n` แสดงเลขพอร์ตไม่แปลงเป็นชื่อ, `-p` แสดง process (ต้อง sudo)
`127.0.0.1:8080` = รับเฉพาะในเครื่อง, `0.0.0.0:80` = รับจากทุกที่
`sudo ss -tlnp | grep 8081` = กรองเหลือแค่บรรทัดที่มี `8081` ไม่มีผลลัพธ์ = ไม่มีใครฟังพอร์ตนั้น

## `curl` flag ที่ใช้บ่อย
`-I` = ขอแค่ header (ส่งเป็น `HEAD` ไม่ใช่ `GET`)
`-v` = แสดงทุกอย่างทั้ง request และ response header, `-s` = เงียบ ไม่แสดง progress
`-H "ชื่อ: ค่า"` = ใส่ header ไปกับ request, `-L` = ตาม redirect
`-o /dev/null` = ทิ้ง body, `-D -` = พิมพ์ response header ออกจอ (`-` = stdout)

## เช็คด้วย `curl` ว่า response ถูก gzip ไหม
`curl -s -o /dev/null -D - -H "Accept-Encoding: gzip" <URL>` แล้วดูว่ามี `Content-Encoding: gzip` ไหม
ต้องใส่ `Accept-Encoding` เอง เพราะ curl ไม่บอก server ว่ารับ gzip ได้ (เบราว์เซอร์บอกเสมอ)
ใช้ `GET` แบบนี้แทน `-I` เพราะ `HEAD` อาจได้ header ไม่ตรงกับตอนขอจริง
`--http1.0` / `--http1.1` = บังคับเวอร์ชัน HTTP ใช้เทียบผลได้

## host key fingerprint ของ SSH คืออะไร
ลายนิ้วมือของ public key ประจำเครื่อง server ใช้ยืนยันว่าต่อเข้าเครื่องตัวจริง
ดูบน server: `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`
ดูค่าที่เครื่องเราจำไว้: `ssh-keygen -lF <IP>` (อ่านจาก `~/.ssh/known_hosts`)

## `ssh-keygen -lf <ไฟล์>` แต่ละ flag คืออะไร
`-l` = list: แสดง fingerprint ของ key
`-f <ไฟล์>` = key ไฟล์ไหน (`-f -` = อ่านจาก stdin เช่นต่อจาก `ssh-keyscan`)
ระวัง `-F` ตัวใหญ่ = find: หา host ใน `known_hosts` คนละความหมายกับ `-f`

## host key ของเครื่อง กับ key ที่ใช้ login ต่างกันยังไง
host key (`/etc/ssh/ssh_host_*_key.pub`) = ประจำเครื่อง server, `sshd` ใช้ยืนยันว่า "ฉันคือเครื่องตัวจริง"
key ที่ใช้ login (`~/.ssh/id_ed25519`) = ประจำตัวคน ใช้ยืนยันว่า "ฉันคือ user นี้"
พิสูจน์คนละทาง: host key กันต่อผิดเครื่อง, login key แทนรหัสผ่าน

## nginx บน Ubuntu: `sites-available` กับ `sites-enabled`
`sites-available/` = เก็บ config ทุกเว็บ, `sites-enabled/` = symlink ไปยังตัวที่เปิดใช้
nginx อ่านแค่ `sites-enabled/` เปิดเว็บ: `sudo ln -s /etc/nginx/sites-available/x /etc/nginx/sites-enabled/`
ปิดเว็บ: ลบ symlink ทิ้ง (ไฟล์ต้นฉบับยังอยู่)

## `systemctl reload` กับ `restart` ต่างกันยังไง
`reload` = อ่าน config ใหม่ ไม่ตัด connection ที่มีอยู่ (nginx รองรับ)
`restart` = หยุดแล้วเริ่มใหม่ เว็บดับชั่วครู่
ใช้ `sudo nginx -t && sudo systemctl reload nginx` เพื่อให้ reload เกิดเฉพาะเมื่อ config ผ่าน

## nginx `gzip on` อย่างเดียวบีบอัดอะไรบ้าง
แค่ `text/html`
ไฟล์ชนิดอื่น (json, js, css) ต้องระบุใน `gzip_types` เช่น `gzip_types application/json application/javascript text/css;`

## nginx `proxy_pass` ส่ง request ต่อด้วย HTTP เวอร์ชันไหน
ค่าเริ่มต้นคือ `HTTP/1.0` แม้เบราว์เซอร์จะส่งมาเป็น 1.1
แก้ด้วย `proxy_http_version 1.1;` ในบล็อกที่มี `proxy_pass`

## nginx สองชั้น (proxy → container) แล้ว `draws.json` ไม่ถูก gzip เพราะอะไร
ชั้นนอกส่งต่อเป็น `HTTP/1.0` (ค่าเริ่มต้นของ `proxy_pass`)
ชั้นในมี `gzip_http_version 1.1` เป็นค่าเริ่มต้น = ไม่ gzip ให้ request 1.0 เลยส่งไฟล์ดิบกลับ
ชั้นนอกมี `gzip on` แต่ไม่มี `gzip_types` จึงบีบแค่ HTML สุดท้าย JSON ไม่ถูกบีบเลยทั้งสองชั้น
แก้: `proxy_http_version 1.1;` ที่ชั้นนอก พิสูจน์: `curl` ตรงเข้า container ด้วย `--http1.0` เทียบกับ `--http1.1`

## `cmd1 && cmd2` กับ `cmd1; cmd2`
`&&` = รัน `cmd2` เฉพาะเมื่อ `cmd1` สำเร็จ (exit code 0)
`;` = รัน `cmd2` เสมอ ไม่สนผลของ `cmd1`

## `|` (pipe) คืออะไร
เอาสิ่งที่คำสั่งซ้ายพิมพ์ออกมา ส่งเป็น input (stdin) ของคำสั่งขวา แทนที่จะแสดงบนจอ
`echo "$TOKEN" | docker login ... --password-stdin` = ส่ง token เข้า stdin ของ `docker login`
`ss -tlnp | grep 8081` = ส่งผลของ `ss` ให้ `grep` กรอง

## ทำไมเขียน `"$TOKEN"` มีเครื่องหมายคำพูด
ให้ shell ส่งค่าเป็นก้อนเดียว
ไม่มีคำพูด + ค่ามีช่องว่างหรืออักขระพิเศษ → shell แยกเป็นหลายท่อน หรือขยาย `*` ให้
นิสัยที่ดี: ใส่ `"..."` ครอบตัวแปรเสมอ

## `IMAGE_TAG=sha-bbb docker compose up -d` (ตัวแปรนำหน้าคำสั่ง) คืออะไร
ตั้ง env var ให้คำสั่งนั้นคำสั่งเดียว พอจบก็หายไป ไม่ค้างใน shell
ต่างจาก `export IMAGE_TAG=...` ที่ค้างอยู่ให้ทุกคำสั่งถัดไป

## `set -e` ใน shell script คืออะไร
`set` = คำสั่งของ shell ไว้เปิด/ปิด option ของ shell เอง, `-e` = exit on error
คำสั่งไหนล้มเหลว (exit code ไม่ใช่ 0) script หยุดทันที
ไม่ใส่ = พังกลางทางแต่รันต่อ และ exit code ของ script = ของคำสั่งสุดท้าย (อาจออกมาเหมือนสำเร็จ)
ใน `appleboy/ssh-action` ใช้แทน option `script_stop` ที่ถูกถอดออกแล้ว: ไม่มี = `pull` พังแต่ step ขึ้นเขียว

## `set -x` คืออะไร
พิมพ์ทุกคำสั่งออกมาก่อนรัน (ขึ้นต้นด้วย `+`) ใช้ตอน debug ว่า script ทำถึงไหนและค่าตัวแปรเป็นอะไร
ระวัง: ค่าลับในคำสั่งจะโผล่ใน log ด้วย

## `trap 'คำสั่ง' EXIT` คืออะไร
ลงทะเบียนคำสั่งให้รันตอน script จบ ไม่ว่าจบเพราะสำเร็จหรือพัง
ใช้เก็บกวาด เช่น `trap 'docker logout ghcr.io' EXIT` คู่กับ `set -e`
ทำไมไม่เขียน `docker logout` ไว้ท้าย script: ถ้า `set -e` หยุดกลางทาง บรรทัดท้ายจะไม่ได้รัน ส่วน `trap` รันทุกกรณี
เทียบ JS: คล้าย `finally { }`

## ทำไม `docker login --password-stdin` แทน `-p`
`-p $TOKEN` ทำให้ token เป็นส่วนหนึ่งของคำสั่ง เห็นได้ใน `ps` และ shell history
`echo "$TOKEN" | docker login ... --password-stdin` ส่งผ่าน stdin ไม่โผล่ในคำสั่ง

## deploy ด้วย `docker compose pull` แล้ว `docker compose up -d` แต่ละตัวทำอะไร
`pull` = ดึง image ตาม tag ใน `compose.yml` (เช่น `:${IMAGE_TAG}`) มาไว้บนเครื่อง ยังไม่แตะ container
`up -d` = compose เห็นว่า image เปลี่ยน จึงสร้าง container ใหม่ให้เองแล้วรันเบื้องหลัง (`-d` = detached)
ไม่ต้อง `down` ก่อน service ที่ image ไม่เปลี่ยนจะไม่ถูกแตะ

## เช็คว่า container รันจาก image ตัวไหนอยู่
`docker inspect --format '{{.Config.Image}}' mui-lotto` → เช่น `ghcr.io/.../mui-lotto:sha-ea8f6aa`
ใช้ยืนยันว่า deploy ได้ sha ใหม่จริง
`{{ }}` ตรงนี้เป็น Go template ของ Docker ไม่เกี่ยวกับ `${{ }}` ของ GitHub Actions
ครอบด้วย `'...'` ให้ shell ส่งไปทั้งก้อนแบบไม่แตะ

## image บน VPS กับบน GHCR อันไหนตัวจริง
GHCR = ที่เก็บถาวร ทุกเวอร์ชันที่เคย push ยังอยู่ (ไม่ลบเองถ้าไม่ได้สั่ง)
VPS = แค่สำเนาที่ pull มาใช้ `prune` ลบแค่สำเนา
image เก่าบน VPS หายไปก็ rollback ได้ เพราะ pull กลับมาจาก GHCR ได้

## rollback ด้วยมือบน VPS ทำยังไง
`cd` ไปโฟลเดอร์ที่มี `compose.yml` แล้ว `IMAGE_TAG=sha-<เก่า> docker compose up -d`
ไม่มี image นั้นในเครื่อง → compose ไป pull จาก registry ให้เอง แล้วสร้าง container ใหม่
image private ต้อง `docker login` ก่อน แล้ว `logout` หลังเสร็จ

## rollback ผ่าน GitHub Actions (ไม่ต้อง SSH)
เปิด run เก่าของ commit ที่ยังดีอยู่ในแท็บ Actions → Re-run all jobs
workflow จะ checkout commit เก่า build (เร็วเพราะมี cache) แล้ว deploy `sha-` ของ commit นั้น
ระวัง: tag `latest` จะถูกย้ายกลับไปชี้ตัวเก่าด้วย

## rollback แล้ว ทำไมยังไม่จบ
rollback ทุกแบบเป็นการแก้ชั่วคราว push เข้า main ครั้งถัดไปจะ deploy โค้ดล่าสุด (ที่ยังพัง) กลับขึ้นมา
แก้ถาวร: `git revert <commit ที่มีปัญหา>` แล้ว push ให้ main กลับเป็นโค้ดที่ดี แล้วปล่อย workflow deploy ตามปกติ

## `docker image prune -f` กับ `-af` ต่างกันยังไง
`-f` = ลบเฉพาะ dangling (image ที่ไม่มี tag แล้ว)
`-af` = ลบทุก image ที่ไม่มี container ใช้ (รวมที่ยังมี tag)
จำกัดขอบเขตด้วย `--filter "label=..."` เพื่อไม่ให้ไปลบ image ของโปรเจกต์อื่น

## ทำไม `docker image prune -f` ไม่พอ เมื่อ tag image ด้วย sha ทุก deploy
image เก่ายังมี tag ของตัวเอง (`sha-aaa`, `sha-bbb`, ...) จึงไม่ถือเป็น dangling
`-f` อย่างเดียว image จะสะสมทุกครั้งที่ deploy ต้องใช้ `-a`
container ที่รันอยู่ปลอดภัย เพราะ `-a` ลบแค่ image ที่ไม่มี container ใช้
ผลข้างเคียง: rollback ไป sha เก่าต้อง `pull` จาก registry ใหม่ เพราะในเครื่องไม่มีแล้ว

## กรอง `docker image prune -af` ให้ลบแค่ image ของ repo เดียวยังไง
`docker/metadata-action` ติด label `org.opencontainers.image.source` (URL ของ repo) ให้ทุก image
`docker image prune -af --filter "label=org.opencontainers.image.source=https://github.com/<owner>/<repo>"`
image ของโปรเจกต์อื่นบนเครื่องเดียวกันไม่มี label นี้ จึงไม่โดนลบ

## ทำไม host fingerprint ถูกแต่ยังขึ้น mismatch
server มี host key หลายชนิด (ED25519, ECDSA, RSA) แต่ละชนิดมี fingerprint ต่างกัน
client กับ server ตกลงกันว่าจะใช้ชนิดไหน: OpenSSH เลือก ED25519 ก่อน แต่ library SSH ของ Go (ที่ appleboy/drone-ssh ใช้) เลือก ECDSA ก่อน
ดูทุกชนิดจากภายนอก: `ssh-keyscan <host> | ssh-keygen -lf -`

## secret ของ GitHub Actions แก้แล้วต้อง push ใหม่ไหม
ไม่ต้อง secret ถูกอ่านตอน job เริ่มรัน กด Re-run failed jobs ได้เลย
secret เปิดดูค่าเดิมไม่ได้ ใส่ทับได้อย่างเดียว
คัดลอก private key ใน PowerShell: `Get-Content <ไฟล์> -Raw | Set-Clipboard` (`-Raw` เก็บบรรทัดใหม่ไว้ครบ)

## `env:` ใน step ของ `appleboy/ssh-action` ทำไม script บน VPS ไม่เห็นตัวแปร
`env:` ตั้ง env var ให้ step บน runner ของ GitHub (คำนวณ `${{ }}` เป็นค่าจริงก่อน)
script ของ appleboy รันบน VPS ซึ่งเป็นอีกเครื่อง ตัวแปรไม่ข้ามไปเอง
ต้องระบุใน `envs: IMAGE_TAG,GHCR_TOKEN` ว่าจะส่งตัวไหนข้ามไป
ภาพจำ: `env:` = ใส่ของลงกระเป๋าบน runner, `envs:` = เลือกชิ้นที่หยิบติดตัวไป VPS
