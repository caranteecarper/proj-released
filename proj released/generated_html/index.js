document.addEventListener('DOMContentLoaded', () => {
    const searchContainer = document.getElementById('search-container');
    if (!searchContainer) {
        alert(`Failed to find "<div class="page-board" id="search-container"></div>".`);
        return;
    }
    // create <startLabel> and <startInput>
    const startLabel = document.createElement('label');
    startLabel.classList.add('search-container-start-date-input-label');
    startLabel.htmlFor = 'search-container-start-date-input';
    startLabel.textContent = '开始日期：';
    const startInput = document.createElement('input');
    startInput.classList.add('search-container-start-date-input');
    startInput.type = 'date';
    // create <endLabel> and <endInput>
    const endLabel = document.createElement('label');
    endLabel.classList.add('search-container-end-date-input-label');
    endLabel.htmlFor = 'search-container-end-date-input';
    endLabel.textContent = '结束日期：';
    const endInput = document.createElement('input');
    endInput.classList.add('search-container-end-date-input');
    endInput.type = 'date';
    // create <clearButton>
    const clearButton = document.createElement('button');
    clearButton.classList.add('search-container-clear-button');
    clearButton.type = 'button';
    clearButton.innerText = '重置筛选器';
    // create <downloadPDFButton>
    const downloadPDFButton = document.createElement('button');
    downloadPDFButton.classList.add('search-container-download-PDF-button');
    downloadPDFButton.type = 'button';
    downloadPDFButton.innerText = '下载PDF';
    // append <startLabel>, <startInput>, <endLabel>, <endInput>, <clearButton>, and <downloadPDFButton> to <searchContainer>
    searchContainer.append(startLabel, startInput, endLabel, endInput, clearButton, downloadPDFButton);
    // find all the page boards and corresponding page board items
    const pageBoardsInfo = [
        /*
        * {
        *       pageBoard: HTMLDivElement,
        *       pageBoardItems: HTMLDivElement[]
        * }
        * */
    ];
    document.querySelectorAll('div.page-board').forEach((pageBoard) => {
        const pageBoardItems = [];
        pageBoard.querySelectorAll('div.page-board-item').forEach((pageBoardItem) => {
            pageBoardItems.push(pageBoardItem);
        });
        if (pageBoardItems.length > 0) {
            pageBoardsInfo.push({
                'pageBoard': pageBoard,
                'pageBoardItems': pageBoardItems
            });
        }
    });
    if (pageBoardsInfo.length <= 0) {
        alert(`Failed to find any valid page board.`);
        return;
    }
    // listen to any changes on <startInput> and <endInput>
    startInput.addEventListener('change', () => filterByDate());
    endInput.addEventListener('change', () => filterByDate());
    // listen to clicking on <clearButton>
    clearButton.addEventListener('click', () => {
        startInput.value = endInput.value = '';
        filterByDate();
    });
    // listen to clicking on <downloadPDFButton>
    downloadPDFButton.addEventListener('click', function downloadPDFButtonEventListener() {
        downloadPDFButton.removeEventListener('click', downloadPDFButtonEventListener);
        downloadPDFButton.innerText = '正在加载PDF文件...';
        try {
            // Set the desired fixed PDF width
            const pdfWidth = 1100 + Math.abs(1100 - document.body.scrollWidth) / 3; // Fixed width in px
            const pdfHeight = document.body.scrollHeight + 100;
            html2pdf()
                .set({
                    margin: 0,
                    image: {type: 'jpeg', quality: 0.75},
                    html2canvas: {scale: 3},
                    jsPDF: {unit: 'px', format: [pdfWidth, pdfHeight], orientation: 'portrait'},
                })
                .from(document.body)
                .toPdf()
                .get('pdf')
                .then((pdfObj) => {
                    // Create a temporary URL for the Blob
                    const url = URL.createObjectURL(
                        new Blob([pdfObj.output('arraybuffer')], {type: 'application/pdf'})
                    );
                    // Create a temporary <a> element to trigger download
                    const alink = document.createElement('a');
                    alink.href = url;
                    alink.download = 'page.pdf'; // The downloaded filename
                    // document.appendChild(alink);
                    alink.click();
                    URL.revokeObjectURL(url);
                    // document.removeChild(alink);
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

    // filter items by selected date range
    function filterByDate() {
        const startDate = startInput.value ? parseDateString(startInput.value) : null;
        const endDate = endInput.value ? parseDateString(endInput.value) : null;
        pageBoardsInfo.forEach((pageBoardInfo) => {
            const
                pageBoard = pageBoardInfo['pageBoard'],
                pageBoardItems = pageBoardInfo['pageBoardItems'];
            let hiddenItemsCounter = 0;
            pageBoardItems.forEach((pageBoardItem) => {
                const span = pageBoardItem.querySelector('span');
                if (span === null) { // no date span → hide
                    pageBoardItem.style.display = 'none'; // hide
                    hiddenItemsCounter++;
                    return;
                }
                const date = parseDateString(span.textContent.trim());
                if (date === null) { // failed to parse date string → show
                    alert(`无法转换日期格式 "${span.textContent.trim()}".`);
                    pageBoardItem.style.display = 'block'; // show
                    return;
                }
                // console.log(span.textContent.trim());
                if ((startDate !== null && date.valueOf() < startDate.valueOf())
                    || (endDate !== null && date.valueOf() > endDate.valueOf())) {
                    hiddenItemsCounter++;
                    pageBoardItem.style.display = 'none'; // hide
                    return;
                }
                // console.log( // test whether the range is kept correctly
                //     `startDate=${dateToString(startDate)}, date=${dateToString(date)}, endDate=${dateToString(endDate)}.`
                // );
                pageBoardItem.style.display = 'block'; // show
            });
            if (hiddenItemsCounter === pageBoardItems.length) { // all the page board items are hidden
                pageBoard.style.display = 'none'; // hide the page board
            } else { // Some of the page board items are shown
                pageBoard.style.display = 'block'; // show the page board
            }
        });

        function parseDateString(str) {
            for (const reg of [
                /^(\d{4})年(\d{1,2})月(\d{1,2})日$/,  // Chinese format: "2025年6月23日"
                /^(\d{4})-(\d{1,2})-(\d{1,2})$/,     // English format 1: "2025-06-23"
                /^(\d{4})\/(\d{1,2})\/(\d{1,2})$/,   // English format 2: "2025/06/23"
                /^(\d{4})\.(\d{1,2})\.(\d{1,2})$/,   // English format 3: "2025.06.23"
            ]) {
                const m = str.match(reg);
                if (m !== null) {
                    const [_, yr, mon, day] = m;
                    return new Date(`${yr}-${mon}-${day}`);
                }
            }
            return null;
        }
    }

    // helper function primarily for code testing
    function dateToString(date) {
        if (date === null) {
            return 'null';
        }
        const
            year = date.getFullYear(),
            month = String(date.getMonth() + 1).padStart(2, '0'), // Months are zero-indexed
            day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
});