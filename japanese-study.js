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
const recognizedLines = document.getElementById('recognizedLines');
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

// 处理粘贴事件
document.addEventListener('paste', (e) => {
    e.preventDefault();
    const items = e.clipboardData.items;

    for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
            const file = items[i].getAsFile();
            handleFile(file);
            
            // 显示成功提示
            const uploadLabel = document.querySelector('.upload-label');
            const originalText = uploadLabel.innerHTML;
            uploadLabel.innerHTML = '图片已成功粘贴！';
            
            setTimeout(() => {
                uploadLabel.innerHTML = originalText;
            }, 2000);
            
            break;
        }
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
    if (!file || !file.type.startsWith('image/')) {
        alert('请上传有效的图片文件');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        preview.src = e.target.result;
        preview.style.display = 'block';
        
        // 调整预览图片大小
        preview.onload = () => {
            if (preview.naturalWidth > 800) {
                preview.style.width = '800px';
            }
        };
    };
    reader.onerror = () => {
        alert('读取图片失败，请重试');
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
    recognizedLines.innerHTML = ''; // 清空之前的结果
    
    try {
        const result = await worker.recognize(preview.src);
        const lines = result.data.lines;
        
        // 处理每一行文本
        lines.forEach((line, index) => {
            const confidence = line.confidence;
            // 只显示置信度大于30的结果
            if (confidence > 30) {
                const lineElement = document.createElement('div');
                lineElement.className = 'recognized-line';
                
                // 创建文本span
                const textSpan = document.createElement('span');
                textSpan.className = 'line-text';
                textSpan.textContent = line.text;
                
                // 创建按钮容器
                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'line-actions';
                
                // 创建按钮
                const useButton = document.createElement('button');
                useButton.className = 'use-text-btn';
                useButton.textContent = '使用此文本';
                useButton.addEventListener('click', () => useText(line.text));
                
                // 组装元素
                actionsDiv.appendChild(useButton);
                lineElement.appendChild(textSpan);
                lineElement.appendChild(actionsDiv);
                
                recognizedLines.appendChild(lineElement);
            }
        });

        if (recognizedLines.children.length === 0) {
            recognizedLines.innerHTML = '<div class="no-results">未能识别出有效文本，请尝试调整图片或重新上传</div>';
        }
    } catch (error) {
        alert('识别失败，请重试');
        console.error(error);
    }
    
    document.getElementById('ocrProgress').style.display = 'none';
});

// 处理识别文本，分离日语和中文
function processText(text) {
    // 移除序号（数字+.）
    text = text.replace(/^\d+\.\s*/, '');
    
    // 移除音调符号
    text = text.replace(/[⓪①②③④]/g, '');
    
    // 移除词性标注 [xxx]
    text = text.replace(/\[[^\]]+\]/g, '');
    
    // 尝试分离日语和中文
    // 假设日语和中文之间可能有空格或其他分隔符
    let parts = text.split(/[\s　]+/);
    
    // 过滤空字符串并获取有效部分
    parts = parts.filter(part => part.trim().length > 0);
    
    if (parts.length >= 2) {
        // 将第一部分作为日语单词，其余部分合并作为中文含义
        return {
            japanese: parts[0].trim(),
            meaning: parts.slice(1).join(' ').trim()
        };
    } else {
        // 如果无法分离，则只返回日语部分
        return {
            japanese: text.trim(),
            meaning: ''
        };
    }
}

// 使用识别出的文本
function useText(text) {
    const processed = processText(text);
    document.getElementById('japaneseWord').value = processed.japanese;
    document.getElementById('meaning').value = processed.meaning;
    
    // 如果中文含义为空，则聚焦到中文输入框
    // 否则聚焦到添加按钮
    if (!processed.meaning) {
        document.getElementById('meaning').focus();
    } else {
        document.getElementById('addWord').focus();
    }
}

// 添加生词
addWordBtn.addEventListener('click', () => {
    const japaneseWord = document.getElementById('japaneseWord').value.trim();
    const meaning = document.getElementById('meaning').value.trim();

    if (!japaneseWord || !meaning) {
        alert('请填写完整的单词信息');
        return;
    }

    const word = {
        id: Date.now(),
        japanese: japaneseWord,
        meaning: meaning
    };

    vocabulary.push(word);
    localStorage.setItem('vocabulary', JSON.stringify(vocabulary));
    
    document.getElementById('japaneseWord').value = '';
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
