const input = document.getElementById('photoInput');
const promptInput = document.getElementById('promptInput');
const btn = document.getElementById('generateBtn');
const statusEl = document.getElementById('status');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const downloadLink = document.getElementById('downloadLink');

let avatar = null;

const KEYWORDS = {
  wave: ['你好', 'hello', 'hi', '再见', '挥手', '拜拜'],
  nod: ['同意', '好的', '收到', 'ok', '可以'],
  shake: ['不要', '不行', '拒绝', '不'],
  bounce: ['开心', '庆祝', '耶', '激动', '哈哈'],
};

input.addEventListener('change', () => {
  const file = input.files[0];
  if (!file) return;
  const img = new Image();
  img.onload = () => {
    avatar = img;
    drawFrame(0, 'wave', promptInput.value || '预览');
  };
  img.src = URL.createObjectURL(file);
});

function inferMotion(text) {
  const lowered = text.toLowerCase();
  for (const [motion, words] of Object.entries(KEYWORDS)) {
    if (words.some((w) => lowered.includes(w))) return motion;
  }
  return 'wave';
}

function transform(motion, t) {
  if (motion === 'nod') return { angle: Math.sin(2 * Math.PI * t) * 0.08, dx: 0, dy: Math.abs(Math.sin(2 * Math.PI * t)) * 20 };
  if (motion === 'shake') return { angle: Math.sin(4 * Math.PI * t) * 0.11, dx: Math.sin(4 * Math.PI * t) * 24, dy: 0 };
  if (motion === 'bounce') return { angle: 0, dx: 0, dy: -Math.abs(Math.sin(2 * Math.PI * t)) * 26 };
  return { angle: Math.sin(2 * Math.PI * t) * 0.17, dx: Math.sin(2 * Math.PI * t) * 18, dy: 0 };
}

function drawCaption(text) {
  const msg = (text || '表情包生成中').slice(0, 20);
  ctx.fillStyle = 'rgba(0,0,0,.6)';
  ctx.fillRect(20, canvas.height - 64, canvas.width - 40, 44);
  ctx.fillStyle = '#fff';
  ctx.font = '20px sans-serif';
  ctx.fillText(msg, 30, canvas.height - 34);
}

function drawFrame(t, motion, text) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (!avatar) return;

  const fit = Math.min((canvas.width - 70) / avatar.width, (canvas.height - 90) / avatar.height);
  const w = avatar.width * fit;
  const h = avatar.height * fit;

  const { angle, dx, dy } = transform(motion, t);
  ctx.save();
  ctx.translate(canvas.width / 2 + dx, canvas.height / 2 + dy);
  ctx.rotate(angle);
  ctx.drawImage(avatar, -w / 2, -h / 2, w, h);
  ctx.restore();

  drawCaption(text);
}

btn.addEventListener('click', () => {
  if (!avatar) {
    statusEl.textContent = '请先上传照片';
    return;
  }

  const text = promptInput.value.trim();
  const motion = inferMotion(text);
  statusEl.textContent = `正在生成：${motion}...`;
  downloadLink.classList.add('disabled');

  const gif = new GIF({
    workers: 2,
    quality: 10,
    width: 512,
    height: 512,
    workerScript: 'https://cdn.jsdelivr.net/npm/gif.js.optimized/dist/gif.worker.js',
  });

  const total = 20;
  for (let i = 0; i < total; i += 1) {
    drawFrame(i / total, motion, text);
    gif.addFrame(ctx, { copy: true, delay: 80 });
  }

  gif.on('finished', (blob) => {
    const url = URL.createObjectURL(blob);
    downloadLink.href = url;
    downloadLink.classList.remove('disabled');
    statusEl.textContent = '生成完成，可下载 GIF。';
  });

  gif.render();
});
