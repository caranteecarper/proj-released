document.addEventListener('DOMContentLoaded', () => {
    const searchContainer = document.getElementById('search-container');
    if (!searchContainer) {
        alert('未找到搜索容器 search-container');
        return;
    }

    // UI: 日期筛选 + 重置 + 下载 PDF
    const startLabel = document.createElement('label');
    startLabel.classList.add('search-container-start-date-input-label');
    startLabel.htmlFor = 'search-container-start-date-input';
    startLabel.textContent = '开始日期：';

    const startInput = document.createElement('input');
    startInput.classList.add('search-container-start-date-input');
    startInput.type = 'date';
    startInput.id = 'search-container-start-date-input';

    const endLabel = document.createElement('label');
    endLabel.classList.add('search-container-end-date-input-label');
    endLabel.htmlFor = 'search-container-end-date-input';
    endLabel.textContent = '结束日期：';

    const endInput = document.createElement('input');
    endInput.classList.add('search-container-end-date-input');
    endInput.type = 'date';
    endInput.id = 'search-container-end-date-input';

    const clearButton = document.createElement('button');
    clearButton.classList.add('search-container-clear-button');
    clearButton.type = 'button';
    clearButton.innerText = '重置筛选器';

    const downloadPDFButton = document.createElement('button');
    downloadPDFButton.classList.add('search-container-download-PDF-button');
    downloadPDFButton.type = 'button';
    downloadPDFButton.innerText = '下载PDF';

    searchContainer.append(startLabel, startInput, endLabel, endInput, clearButton, downloadPDFButton);

    // 收集每个板块及其条目
    const pageBoardsInfo = [];
    document.querySelectorAll('div.page-board').forEach((pageBoard) => {
        const pageBoardItems = [];
        pageBoard.querySelectorAll('div.page-board-item').forEach((pageBoardItem) => {
            pageBoardItems.push(pageBoardItem);
        });
        if (pageBoardItems.length > 0) {
            pageBoardsInfo.push({ pageBoard, pageBoardItems });
        }
    });
    if (pageBoardsInfo.length <= 0) {
        alert('未找到任何列表板块');
        return;
    }

    // 事件绑定
    startInput.addEventListener('change', filterByDate);
    endInput.addEventListener('change', filterByDate);
    clearButton.addEventListener('click', () => {
        startInput.value = endInput.value = '';
        filterByDate();
    });
    downloadPDFButton.addEventListener('click', function downloadPDFButtonEventListener() {
        downloadPDFButton.removeEventListener('click', downloadPDFButtonEventListener);
        downloadPDFButton.innerText = '正在加载PDF文件...';
        try {
            const pdfWidth = 1100 + Math.abs(1100 - document.body.scrollWidth) / 3;
            const pdfHeight = document.body.scrollHeight + 100;
            html2pdf()
                .set({
                    margin: 0,
                    image: { type: 'jpeg', quality: 0.75 },
                    html2canvas: { scale: 3 },
                    jsPDF: { unit: 'px', format: [pdfWidth, pdfHeight], orientation: 'portrait' },
                })
                .from(document.body)
                .toPdf()
                .get('pdf')
                .then((pdfObj) => {
                    const url = URL.createObjectURL(new Blob([pdfObj.output('arraybuffer')], { type: 'application/pdf' }));
                    const alink = document.createElement('a');
                    alink.href = url;
                    alink.download = 'page.pdf';
                    alink.click();
                    URL.revokeObjectURL(url);
                })
                .then(() => {
                    downloadPDFButton.addEventListener('click', downloadPDFButtonEventListener);
                    downloadPDFButton.innerText = '下载PDF';
                });
        } catch (e) {
            downloadPDFButton.innerText = '生成PDF失败';
            throw e;
        }
    });

    // 日期筛选
    function filterByDate() {
        const startDate = startInput.value ? parseDateString(startInput.value) : null;
        const endDate = endInput.value ? parseDateString(endInput.value) : null;
        pageBoardsInfo.forEach(({ pageBoard, pageBoardItems }) => {
            let hiddenItemsCounter = 0;
            pageBoardItems.forEach((pageBoardItem) => {
                const span = pageBoardItem.querySelector('span');
                if (span === null) {
                    pageBoardItem.style.display = 'none';
                    hiddenItemsCounter++;
                    return;
                }
                const date = parseDateString(span.textContent.trim());
                if (date === null) {
                    // 无法识别的日期：隐藏，避免干扰筛选
                    pageBoardItem.style.display = 'none';
                    hiddenItemsCounter++;
                    return;
                }
                if ((startDate !== null && date.valueOf() < startDate.valueOf())
                    || (endDate !== null && date.valueOf() > endDate.valueOf())) {
                    hiddenItemsCounter++;
                    pageBoardItem.style.display = 'none';
                    return;
                }
                pageBoardItem.style.display = 'block';
            });
            if (hiddenItemsCounter === pageBoardItems.length) {
                pageBoard.style.display = 'none';
            } else {
                pageBoard.style.display = 'block';
            }
        });
    }

    // 更宽松的日期解析：支持 YYYY-MM-DD / YYYY.MM.DD / YYYY/MM/DD / YYYY年MM月DD日 等
    function parseDateString(str) {
        if (!str) return null;
        const patterns = [
            /^(\d{4})\s*[年\-\/\.]\s*(\d{1,2})\s*[月\-\/\.]\s*(\d{1,2})\s*[日号]?$/,
            /^(\d{4})-(\d{1,2})-(\d{1,2})$/,
            /^(\d{4})\/(\d{1,2})\/(\d{1,2})$/,
            /^(\d{4})\.(\d{1,2})\.(\d{1,2})$/,
        ];
        for (const reg of patterns) {
            const m = str.match(reg);
            if (m) {
                const yr = m[1], mon = m[2], day = m[3];
                return new Date(`${yr}-${mon}-${day}`);
            }
        }
        const nums = str.match(/(\d{4}).*?(\d{1,2}).*?(\d{1,2})/);
        if (nums) {
            const yr = nums[1], mon = nums[2], day = nums[3];
            return new Date(`${yr}-${mon}-${day}`);
        }
        return null;
    }
});
