// 时间相关功能
function updateTime() {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleTimeString();
    document.getElementById('current-date').textContent = now.toLocaleDateString();
}

setInterval(updateTime, 1000);
updateTime();

let stopwatch = {
    running: false,
    startTime: 0,
    interval: null
};

function startStopwatch() {
    if (!stopwatch.running) {
        stopwatch.startTime = Date.now();
        stopwatch.interval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - stopwatch.startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            alert(`${minutes}分${seconds}秒`);
        }, 1000);
        stopwatch.running = true;
    } else {
        clearInterval(stopwatch.interval);
        stopwatch.running = false;
    }
}

// 便签本功能
function saveNote() {
    const note = document.getElementById('notepad').value;
    localStorage.setItem('saved_note', note);
    alert('笔记已保存！');
}

// 加载保存的笔记
document.getElementById('notepad').value = localStorage.getItem('saved_note') || '';

// 计算器功能
function calculate() {
    const input = document.getElementById('calc-input').value;
    try {
        const result = eval(input);
        document.getElementById('calc-result').textContent = `结果: ${result}`;
    } catch (error) {
        document.getElementById('calc-result').textContent = '输入有误';
    }
}

// 待办事项功能
function addTodo() {
    const input = document.getElementById('todo-input');
    const text = input.value.trim();
    
    if (text) {
        const list = document.getElementById('todo-list');
        const li = document.createElement('li');
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        
        const span = document.createElement('span');
        span.textContent = text;
        
        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = '删除';
        deleteBtn.onclick = () => li.remove();
        
        li.appendChild(checkbox);
        li.appendChild(span);
        li.appendChild(deleteBtn);
        list.appendChild(li);
        
        input.value = '';
    }
}

// 启动计时器
function startTimer() {
    const minutes = prompt('请输入分钟数：');
    if (minutes && !isNaN(minutes)) {
        const milliseconds = minutes * 60 * 1000;
        setTimeout(() => {
            alert('时间到！');
        }, milliseconds);
    }
}

// 初始化Tesseract
const worker = Tesseract.createWorker({
    logger: progress => {
        if (progress.status === 'recognizing text') {
            document.querySelector('.progress').style.width = `${progress.progress * 100}%`;
        }
    }
});

// 初始化变量
let vocabulary = JSON.parse(localStorage.getItem('vocabulary') || '[]');
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const preview = document.getElementById('preview');
const startOCR = document.getElementById('startOCR');
const recognizedText = document.getElementById('recognizedText');
const addWordBtn = document.getElementById('addWord');
const vocabularyList = document.getElementById('vocabularyList');

// 初始化Tesseract worker
async function initWorker() {
    await worker.load();
    await worker.loadLanguage('jpn');
    await worker.initialize('jpn');
}

initWorker();

// 处理文件拖放
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#0071e3';
});

dropZone.addEventListener('dragleave', () => {
    dropZone.style.borderColor = '#d2d2d7';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#d2d2d7';
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
        handleFile(file);
    }
});

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
});

// 处理文件上传
function handleFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        preview.src = e.target.result;
        preview.style.display = 'block';
    };
    reader.readAsDataURL(file);
}

// OCR识别
startOCR.addEventListener('click', async () => {
    if (!preview.src) {
        alert('请先上传图片');
        return;
    }

    document.getElementById('ocrProgress').style.display = 'block';
    document.querySelector('.progress').style.width = '0%';
    
    try {
        const result = await worker.recognize(preview.src);
        recognizedText.value = result.data.text;
    } catch (error) {
        alert('识别失败，请重试');
        console.error(error);
    }
    
    document.getElementById('ocrProgress').style.display = 'none';
});

// 添加生词
addWordBtn.addEventListener('click', () => {
    const japaneseWord = document.getElementById('japaneseWord').value.trim();
    const reading = document.getElementById('reading').value.trim();
    const meaning = document.getElementById('meaning').value.trim();

    if (!japaneseWord || !reading || !meaning) {
        alert('请填写完整的单词信息');
        return;
    }

    const word = {
        id: Date.now(),
        japanese: japaneseWord,
        reading: reading,
        meaning: meaning
    };

    vocabulary.push(word);
    localStorage.setItem('vocabulary', JSON.stringify(vocabulary));
    
    document.getElementById('japaneseWord').value = '';
    document.getElementById('reading').value = '';
    document.getElementById('meaning').value = '';
    
    renderVocabulary();
});

// 渲染生词本
function renderVocabulary() {
    vocabularyList.innerHTML = '';
    vocabulary.forEach(word => {
        const wordCard = document.createElement('div');
        wordCard.className = 'word-card';
        wordCard.innerHTML = `
            <div class="word-info">
                <div class="word-japanese">${word.japanese}</div>
                <div class="word-reading">${word.reading}</div>
                <div class="word-meaning">${word.meaning}</div>
            </div>
            <button class="delete-word" onclick="deleteWord(${word.id})">删除</button>
        `;
        vocabularyList.appendChild(wordCard);
    });
}

// 删除生词
function deleteWord(id) {
    vocabulary = vocabulary.filter(word => word.id !== id);
    localStorage.setItem('vocabulary', JSON.stringify(vocabulary));
    renderVocabulary();
}

// 初始化渲染生词本
renderVocabulary();

// URL缩短和剪贴板功能
async function shortenUrl() {
    const urlInput = document.getElementById('urlInput');
    const shortUrlElement = document.getElementById('shortUrl');
    const copyButton = document.getElementById('copyButton');
    const url = urlInput.value;

    if (!url) {
        alert('Please enter a URL');
        return;
    }

    try {
        const response = await fetch('/shorten', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();
        
        if (response.ok) {
            shortUrlElement.textContent = data.short_url;
            copyButton.style.display = 'inline-block';
        } else {
            shortUrlElement.textContent = 'Error: ' + data.error;
            copyButton.style.display = 'none';
        }
    } catch (error) {
        shortUrlElement.textContent = 'Error: Could not shorten URL';
        copyButton.style.display = 'none';
    }
}

async function copyToClipboard() {
    const shortUrl = document.getElementById('shortUrl').textContent;
    try {
        await navigator.clipboard.writeText(shortUrl);
        alert('Copied to clipboard!');
    } catch (err) {
        alert('Failed to copy to clipboard');
    }
}

document.getElementById('shortenButton').addEventListener('click', shortenUrl);
document.getElementById('copyButton').addEventListener('click', copyToClipboard);
