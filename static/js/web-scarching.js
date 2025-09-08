// Đảm bảo rằng DOM đã được tải đầy đủ trước khi khởi tạo biểu đồ và các sự kiện
document.addEventListener('DOMContentLoaded', function() {
    // --- KHỞI TẠO BIỂU ĐỒ ---

    // Biểu đồ tròn với cấu hình được sửa để hiển thị đầy đủ
    const pieCtx = document.getElementById('pieChart');
    if (pieCtx) { // Thêm kiểm tra null để an toàn hơn
        const pieChart = new Chart(pieCtx.getContext('2d'), {
            type: 'pie',
            data: {
                labels: ['loigiaihay.com', 'vietjack.com', 'loigia8r.vn', 'aaa', 'bbbb'],
                datasets: [{
                    data: [30, 25, 20, 15, 10],
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#333',
                            font: {
                                size: 12
                            },
                            padding: 15,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    } else {
        console.error("Phần tử 'pieChart' không tìm thấy trong DOM. Biểu đồ tròn không được khởi tạo.");
    }

    // Bar chart with modified configuration to display crawled website counts
    const barCtx = document.getElementById('barChart');
    if (barCtx) { // Thêm kiểm tra null để an toàn hơn
        const barChart = new Chart(barCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['Toán', 'Ngữ Văn', 'Tiếng Anh', 'Vật Lý', 'Hóa Học', 'Lịch Sử', 'Địa Lý', 'Tiếng Việt', 'Tự nhiên & Xã hội'],
                datasets: [
                    {
                        label: 'THPT',
                        data: [150, 120, 180, 90, 110, null, null, null, null],
                        backgroundColor: '#FF6384',
                        borderRadius: 8,
                    },
                    {
                        label: 'THCS',
                        data: [100, 130, 110, null, null, 80, 75, null, null],
                        backgroundColor: '#36A2EB',
                        borderRadius: 8,
                    },
                    {
                        label: 'Tiểu học',
                        data: [200, null, null, null, null, null, null, 160, 140],
                        backgroundColor: '#FFCE56',
                        borderRadius: 8,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 250,
                        ticks: {
                            color: '#333'
                        },
                        title: {
                            display: true,
                            text: 'Số lượng trang web đã cào',
                            color: '#555'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#333'
                        },
                        title: {
                            display: true,
                            text: 'Môn học',
                            color: '#555'
                        }
                    }
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#333',
                            font: {
                                size: 14
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.7)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#ddd',
                        borderWidth: 1,
                        cornerRadius: 8,
                    }
                }
            }
        });
    } else {
        console.error("Phần tử 'barChart' không tìm thấy trong DOM. Biểu đồ cột không được khởi tạo.");
    }

    // --- CÁC BIẾN VÀ HÀM XỬ LÝ URL ---

    let urlList = [];
    let isProcessing = false;

    // Lấy các phần tử DOM và thêm kiểm tra null
    const fileUploadArea = document.getElementById('fileUploadArea');
    const fileInput = document.getElementById('fileInput');
    const singleUrlInput = document.getElementById('singleUrl');
    const addUrlButton = document.querySelector('.input-group .btn'); // Nút "Thêm URL"
    const selectAllBtn = document.querySelector('.control-buttons .btn'); // Nút "Chọn tất cả"
    const deleteSelectedBtn = document.querySelector('.bottom-controls .btn-danger'); // Nút "Xóa đã chọn"
    const processSelectedBtn = document.querySelector('.bottom-controls .btn-success'); // Nút "Xử lý đã chọn"
    const linkListDiv = document.getElementById('linkList');
    const bottomControlsDiv = document.getElementById('bottomControls');
    const processingInfoDiv = document.getElementById('processingInfo');
    const processStatusSpan = document.getElementById('processStatus');
    const recentLinksDiv = document.getElementById('recentLinks');


    // Thêm các Event Listener
    if (fileUploadArea) {
        fileUploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            fileUploadArea.classList.add('dragover');
        });

        fileUploadArea.addEventListener('dragleave', () => {
            fileUploadArea.classList.remove('dragover');
        });

        fileUploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            fileUploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });
    }

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });
    }

    if (addUrlButton) {
        addUrlButton.addEventListener('click', addSingleUrl);
    }

    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', selectAll);
    }

    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', deleteSelected);
    }

    if (processSelectedBtn) {
        processSelectedBtn.addEventListener('click', processSelected);
    }

    // Khởi tạo danh sách URL khi DOM đã sẵn sàng (để hiển thị trạng thái "Chưa có URL...")
    updateLinkList();


    // --- ĐỊNH NGHĨA CÁC HÀM ---

    function handleFile(file) {
        // RẤT QUAN TRỌNG: Xóa rỗng danh sách URL mỗi khi một file mới được tải lên
        urlList = [];

        const reader = new FileReader();

        reader.onload = function(e) {
            const content = e.target.result;
            console.log("Nội dung file được đọc:", content);

            let urlsToProcess = [];

            const fileName = file.name;
            const fileExtension = fileName.split('.').pop().toLowerCase();
            console.log("Tên file:", fileName, " - Phần mở rộng:", fileExtension);

            if (fileExtension === 'json') {
                try {
                    const jsonData = JSON.parse(content);
                    if (Array.isArray(jsonData)) {
                        jsonData.forEach(item => {
                            if (typeof item === 'string') {
                                urlsToProcess.push(item);
                            } else if (typeof item === 'object' && item.url) {
                                urlsToProcess.push(item.url);
                            }
                        });
                    }
                    console.log("URLs từ file JSON (sau khi parse):", urlsToProcess);
                } catch (error) {
                    console.error("Lỗi khi parse file JSON:", error);
                    alert("File JSON không hợp lệ hoặc không chứa danh sách URL ở định dạng mong muốn.");
                    return;
                }
            } else if (fileExtension === 'txt' || fileExtension === 'md') {
                urlsToProcess = content.split('\n')
                                .map(line => line.trim())
                                .filter(line => line.length > 0);
                console.log("URLs từ file TXT/MD (sau khi split, trim, filter):", urlsToProcess);
            } else {
                console.warn("Loại file không được hỗ trợ hoặc không có logic xử lý cụ thể:", fileExtension);
                alert("File không phải TXT, JSON, hoặc MD. Vui lòng chọn định dạng file phù hợp.");
                return;
            }

            const urlRegex = /^(https?:\/\/)?(www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(\/\S*)?$/i;
            
            const uniqueAndValidUrls = [];
            urlsToProcess.forEach(url => {
                const trimmedUrl = url.trim();
                const isValidUrl = urlRegex.test(trimmedUrl);
                const isDuplicateInExistingList = urlList.some(item => item.url === trimmedUrl); 

                console.log(`Kiểm tra URL: "${trimmedUrl}" - Khớp Regex: ${isValidUrl} - Trùng lặp (trong list cũ): ${isDuplicateInExistingList}`);

                if (trimmedUrl && isValidUrl && !isDuplicateInExistingList) {
                    uniqueAndValidUrls.push({
                        url: trimmedUrl,
                        status: 'pending',
                        selected: false
                    });
                }
            });
            
            urlList.push(...uniqueAndValidUrls); 
            console.log("Danh sách URL cuối cùng sau khi xử lý:", urlList);

            updateLinkList();
        };

        reader.onerror = function() {
            console.error("Lỗi khi đọc file:", reader.error);
            alert("Có lỗi xảy ra khi đọc file của bạn.");
        };

        reader.readAsText(file);
    }

    function addSingleUrl() {
        const url = singleUrlInput ? singleUrlInput.value.trim() : ''; // Lấy giá trị từ input
        if (url && !urlList.find(item => item.url === url)) {
            urlList.push({
                url: url,
                status: 'pending',
                selected: false
            });
            if (singleUrlInput) singleUrlInput.value = ''; // Xóa input field
            updateLinkList();
        } else if (url) {
             alert("URL này đã có trong danh sách.");
        }
    }

    function updateLinkList() {
        if (!linkListDiv || !bottomControlsDiv) {
            console.warn("Không tìm thấy linkListDiv hoặc bottomControlsDiv. Không thể cập nhật danh sách liên kết.");
            return;
        }

        if (urlList.length === 0) {
            linkListDiv.innerHTML = '<div class="empty-state">Chưa có URL nào được tải lên</div>';
            bottomControlsDiv.style.display = 'none';
            return;
        }
        
        bottomControlsDiv.style.display = 'flex'; 
        
        linkListDiv.innerHTML = urlList.map((item, index) => {
            let actionContent = '';
            
            if (item.status === 'processing') {
                actionContent = `<span class="link-status status-processing">Đang xử lý</span>`;
            } else if (item.status === 'success') {
                actionContent = `<span class="link-status status-success">Hoàn thành</span>`;
            } else if (item.status === 'error') {
                actionContent = `<span class="link-status status-error">Lỗi</span>`;
            } else {
                actionContent = `
                    <div class="link-actions">
                        <input type="checkbox" class="link-checkbox" ${item.selected ? 'checked' : ''} onchange="toggleSelect(${index})">
                        <button class="delete-btn" onclick="deleteUrl(${index})">🗑️</button>
                    </div>
                `;
            }
            
            return `
                <div class="link-item">
                    <a href="${item.url}" class="link-url" target="_blank">${item.url}</a>
                    ${actionContent}
                </div>
            `;
        }).join('');
    }

    // Các hàm phụ trợ được định nghĩa toàn cục trong scope của DOMContentLoaded
    window.toggleSelect = function(index) { // Đặt trong window để có thể gọi từ onclick trong HTML
        if (!isProcessing) {
            urlList[index].selected = !urlList[index].selected;
            updateLinkList();
        }
    }

    window.deleteUrl = function(index) { // Đặt trong window để có thể gọi từ onclick trong HTML
        if (!isProcessing) {
            urlList.splice(index, 1);
            updateLinkList();
        }
    }

    function selectAll() {
        if (!isProcessing) {
            urlList.forEach(item => {
                if (item.status !== 'processing') {
                    item.selected = true;
                }
            });
            updateLinkList();
        }
    }

    function deleteSelected() {
        if (!isProcessing) {
            urlList = urlList.filter(item => !item.selected || item.status === 'processing');
            updateLinkList();
        }
    }

    async function processSelected() {
        const selectedUrls = urlList.filter(item => item.selected && item.status === 'pending');
        if (selectedUrls.length === 0 || isProcessing) {
            alert("Vui lòng chọn ít nhất một URL đang chờ xử lý.");
            return;
        }
        
        isProcessing = true;
        if (processingInfoDiv) {
            processingInfoDiv.classList.add('show');
            if (processStatusSpan) processStatusSpan.textContent = `Đang gửi yêu cầu cào dữ liệu...`;
        }
        
        document.querySelectorAll('.control-buttons button, .bottom-controls button').forEach(btn => btn.disabled = true);
        if (singleUrlInput) singleUrlInput.disabled = true;
        if (fileInput) fileInput.disabled = true;
        if (fileUploadArea) fileUploadArea.style.pointerEvents = 'none';

        async function processOneByOne() {
            let successCount = 0;
            let errorCount = 0;

            for (const itemToProcess of selectedUrls) {
                itemToProcess.status = 'processing';
                updateLinkList();

                if (processStatusSpan) {
                    processStatusSpan.textContent = `Đang xử lý: ${itemToProcess.url}`;
                }

                try {
                        const response = await fetch('/web-scraping/api/crawl', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ url: itemToProcess.url }),
                    });

                    const contentType = response.headers.get("content-type");
                    if (contentType && contentType.indexOf("application/json") !== -1) {
                        const data = await response.json();
                        console.log('Kết quả cào từ server cho', itemToProcess.url, ':', data);
                        if (data.status === 'success') {
                            itemToProcess.status = 'success';
                            successCount++;
                            // Hiển thị thông tin PDF nếu có
                            if (data.pdf_crawl && data.pdf_crawl.total_pdfs > 0) {
                                console.log(`🔥 Found ${data.pdf_crawl.total_pdfs} PDFs:`, data.pdf_crawl.subjects);
                                // Có thể hiển thị notification hoặc update UI
                                showPDFNotification(data.pdf_crawl);
                            }
                        } else {
                            itemToProcess.status = 'error';
                            errorCount++;
                            console.error('Lỗi server cho', itemToProcess.url, ':', data.message);
                        }
                    } else {
                        const errorText = await response.text();
                        throw new Error(`Server returned non-JSON response for ${itemToProcess.url}: ${errorText.substring(0, 100)}...`);
                    }
                } catch (error) {
                    console.error('Lỗi khi gửi yêu cầu cào cho', itemToProcess.url, ':', error);
                    itemToProcess.status = 'error';
                    errorCount++;
                }
                updateLinkList();
            }

            if (processStatusSpan) {
                processStatusSpan.textContent = 
                    `Hoàn thành! Thành công: ${successCount}. Lỗi: ${errorCount}.`;
            }

            urlList.forEach(item => {
                if (item.status === 'success' || item.status === 'error') {
                    addToRecentLinks(item.url, item.status);
                }
            });

        }

        processOneByOne().finally(() => {
            isProcessing = false;
            document.querySelectorAll('.control-buttons button, .bottom-controls button').forEach(btn => btn.disabled = false);
            if (singleUrlInput) singleUrlInput.disabled = false;
            if (fileInput) fileInput.disabled = false;
            if (fileUploadArea) fileUploadArea.style.pointerEvents = 'auto';

            updateLinkList();
            if (processingInfoDiv) {
                setTimeout(() => {
                    processingInfoDiv.classList.remove('show');
                }, 5000);
            }
        });
    }

    function addToRecentLinks(url, status) {
        if (!recentLinksDiv) {
            console.warn("Không tìm thấy phần tử 'recentLinksDiv'. Không thể thêm liên kết gần đây.");
            return;
        }
        const timeString = 'Vừa xong';
        
        const newItem = document.createElement('div');
        newItem.className = 'recent-item';
        newItem.innerHTML = `
            <div>
                <div>${url}</div>
                <div class="recent-time">${timeString}</div>
            </div>
            <div class="status-${status}">${status === 'success' ? 'Thành công' : 'Lỗi'}</div>
        `;
        
        recentLinksDiv.insertBefore(newItem, recentLinksDiv.firstChild);
        
        const items = recentLinksDiv.querySelectorAll('.recent-item');
        if (items.length > 10) {
            items[items.length - 1].remove();
        }
    }

    // cái này cho cái cào pdf 
    function processDeepPDF(detailLinks) {
        return fetch('/web-scraping/api/crawl-deep-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                detail_links: detailLinks,
                max_depth: 3  // Configurable depth
            }),
        });
    }


    function showPDFNotification(pdfData) {
        const notification = document.createElement('div');
        notification.className = 'pdf-notification';
        notification.innerHTML = `
            <div class="pdf-notification-content">
                <h4>🔥 PDF Files Found!</h4>
                <p>Found ${pdfData.total_pdfs} PDF files in subjects: ${pdfData.subjects.join(', ')}</p>
                <small>Saved to: ${pdfData.pdf_file}</small>
            </div>
        `;
        
        // Style the notification
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 1000;
            max-width: 300px;
            animation: slideInRight 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 10 seconds
        setTimeout(() => {
            notification.remove();
        }, 10000);
    }


    // Function to scan for PDF links
    async function scanPDFLinks() {
        try {
            const response = await fetch('/web-scraping/api/scan-pdf-links');
            const data = await response.json();
            
            if (data.status === 'success') {
                console.log('📊 PDF Scan Results:', data);
                showPDFScanResults(data);
            } else {
                console.error('Scan failed:', data.message);
            }
        } catch (error) {
            console.error('Error scanning PDF links:', error);
        }
    }
    // Function to start PDF download
    async function downloadPDFs(maxDownloads = 50) {
        try {
            console.log('🔥 Starting PDF download...');
            
            const response = await fetch('/web-scraping/api/download-pdfs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    max_downloads: maxDownloads,
                    max_per_file: 20
                }),
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                console.log('✅ PDF Download completed:', data);
                showDownloadResults(data);
            } else {
                console.error('Download failed:', data.message);
            }
        } catch (error) {
            console.error('Error downloading PDFs:', error);
        }
    }
    function showPDFScanResults(data) {
    console.log(`Found ${data.total_pdf_links} PDF links in ${data.files_with_pdfs} files`);
    // Update UI to show scan results
    }

    function showDownloadResults(data) {
        console.log(`Downloaded ${data.successful_downloads}/${data.download_attempts} PDFs`);
        console.log('Subjects:', data.subjects);
        console.log('Download directory:', data.download_base_dir);
        // Update UI to show download results
    }


            // Check auto PDF service status
        async function checkPDFServiceStatus() {
            try {
                const response = await fetch('/web-scraping/api/pdf-service/status');
                const data = await response.json();
                
                if (data.status === 'success') {
                    console.log('🤖 Auto PDF Service Status:', data.service);
                    updatePDFServiceUI(data.service);
                }
            } catch (error) {
                console.error('Error checking PDF service:', error);
            }
        }

        // Manually trigger PDF scan
        async function manualPDFScan() {
            try {
                console.log('🔄 Triggering manual PDF scan...');
                const response = await fetch('/web-scraping/api/pdf-service/manual-scan', {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    console.log('✅ Manual scan completed');
                } else {
                    console.error('Manual scan failed:', data.message);
                }
            } catch (error) {
                console.error('Error in manual scan:', error);
            }
        }

        function updatePDFServiceUI(serviceStatus) {
            // Update UI to show service status
            const statusElement = document.getElementById('pdf-service-status');
            if (statusElement) {
                statusElement.innerHTML = `
                    <div class="service-status ${serviceStatus.running ? 'running' : 'stopped'}">
                        <span class="status-indicator"></span>
                        Auto PDF Service: ${serviceStatus.running ? 'Running' : 'Stopped'}
                        <br>
                        <small>
                            Scans every ${serviceStatus.scan_interval_minutes} minutes | 
                            Downloaded: ${serviceStatus.total_downloaded_urls} PDFs
                        </small>
                    </div>
                `;
            }
        }

}); // Kết thúc DOMContentLoaded