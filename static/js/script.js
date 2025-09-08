// Global variables
let selectedDataSource = null;
let selectedFiles = [];
let processingInterval = null;
let currentFileMetadata = null; // THÊM BIẾN NÀY ĐỂ LƯU METADATA HIỆN TẠI
let minioFilesToProcess = []; // Dùng khi chọn từ MinIO folder
// THÊM: Biến global cho chức năng folder
let folderFiles = []; // Danh sách file trong folder
let currentFolderFileIndex = 0; // Index của file hiện tại trong folder
let folderMetadataList = []; // Danh sách metadata của tất cả file trong folder
let isProcessingFolder = false; // Flag để biết đang xử lý folder hay file đơn// NEW GLOBAL VARIABLES FOR SIMULATED RESULTS
let simulatedTotalFilesProcessed = 0;
let simulatedSuccessfullyDownloadedFiles = 0;
let simulatedFailedDownloadFiles = []; // Array of {fileName: string, error: string}
let simulatedTotalChunksGenerated = 0;
let simulatedTotalProcessingTimeMs = 0;
let simulatedProcessStartTime = null;
// THÊM: Variable để track pipeline processing
let pipelineEventSource = null;
let representativeFile = null;
let mongodbInfo = null;
// DOM elements
const fileDropZone = document.getElementById('fileDropZone');
const fileInput = document.getElementById('fileInput');
const chooseFileButton = document.getElementById('chooseFileButton');
const loadFolderButton = document.getElementById('loadFolderButton');
const minioFolderSelect = document.getElementById('minioFolderSelect');
const startProcessingBtn = document.getElementById('startProcessingBtn');
const sourceStatus = document.getElementById('sourceStatus');
const sourceInfo = document.getElementById('sourceInfo');
const defaultMessage = document.getElementById('defaultMessage');
const finalResults = document.getElementById('finalResults');
const finalResultsContent = document.getElementById('finalResultsContent');
const metadataPreviewBox = document.getElementById('metadataPreviewBox');
const saveToMinioBtn = document.getElementById('saveToMinioBtn'); // Thêm nút save
// THÊM: DOM elements cho folder
const folderInput = document.getElementById('folderInput');
const chooseFolderButton = document.getElementById('chooseFolderButton');
const folderInfoBox = document.getElementById('folderInfoBox');
const folderName = document.getElementById('folderName');
const totalFiles = document.getElementById('totalFiles');
const currentFileIndex = document.getElementById('currentFileIndex');
const totalFilesDisplay = document.getElementById('totalFilesDisplay');
const folderNavigationButtons = document.getElementById('folderNavigationButtons');
const prevFileBtn = document.getElementById('prevFileBtn');
const nextFileBtn = document.getElementById('nextFileBtn');
const saveAllToMinioBtn = document.getElementById('saveAllToMinioBtn');

// Progress Step Boxes (assuming these IDs are in your HTML)
const stepBox1 = document.getElementById('stepBox1'); // Load data
const loadDataDescription = stepBox1 ? stepBox1.querySelector('.step-description') : null;

const stepBox2 = document.getElementById('stepBox2'); // Data Extraction
const stepBox3 = document.getElementById('stepBox3'); // Chunking
const stepBox4 = document.getElementById('stepBox4'); // Embedding
const stepBox5 = document.getElementById('stepBox5'); // Save DB

// Progress Arrows (assuming these IDs are in your HTML)
const arrow1 = document.getElementById('arrow1');
const arrow2 = document.getElementById('arrow2');
const arrow3 = document.getElementById('arrow3');
const arrow4 = document.getElementById('arrow4');

// New DOM elements for the initial forms (based on your screenshots)
const dataSourceContainer = document.getElementById('dataSourceContainer'); // Khung chọn nguồn dữ liệu (khung 1)
const processingSection = document.getElementById('processingSection'); // Khung hiển thị kết quả xử lý (khung 2)


// Helper to format Select2 options with icons
function formatFolderOption(folder) {
    if (!folder.id) {
        return folder.text;
    }
    return $('<span>📁 ' + folder.text + '</span>');
}

document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    // Ẩn các phần không cần thiết ban đầu
    if (saveAllToMinioBtn) saveAllToMinioBtn.style.display = 'none'; // THÊM
    if (folderInfoBox) folderInfoBox.style.display = 'none'; // THÊM
    if (folderNavigationButtons) folderNavigationButtons.style.display = 'none'; // THÊM
    if (processingSection) processingSection.style.display = 'none';
    if (metadataPreviewBox) metadataPreviewBox.style.display = 'none';
    if (saveToMinioBtn) saveToMinioBtn.style.display = 'none';
    if (startProcessingBtn) {
        startProcessingBtn.style.display = 'none';
        startProcessingBtn.classList.remove('btn-primary'); // Đảm bảo ban đầu không có màu active
        startProcessingBtn.classList.add('btn-secondary'); // Mặc định là màu xám (disabled look)
    }
    if (finalResults) finalResults.style.display = 'none'; // Đảm bảo kết quả cuối cùng ẩn ban đầu

    // Initialize Select2 if it's not already initialized
    if (minioFolderSelect) {
        if ($(minioFolderSelect).data('select2')) {
            $(minioFolderSelect).select2('destroy');
        }
        $(minioFolderSelect).select2({
            templateResult: formatFolderOption,
            templateSelection: formatFolderOption,
            placeholder: "-- Choose folder --",
            allowClear: true
        });
    }
});

function initializeEventListeners() {
    if (chooseFileButton) {
        chooseFileButton.addEventListener('click', () => {
            // Clear the file input value before clicking, to ensure change event fires even if same file is selected
            if (fileInput) fileInput.value = ''; 
            if (fileInput) fileInput.click();
        });
    }

    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelection);
    }

    if (fileDropZone) {
        fileDropZone.addEventListener('dragover', handleDragOver);
        fileDropZone.addEventListener('dragleave', handleDragLeave);
        fileDropZone.addEventListener('drop', handleFileDrop);
    }

    if (minioFolderSelect) {
        $(minioFolderSelect).on('change', handleMinioFolderSelection); // PHẢI LÀ handleMinioFolderSelection
    }

    if (loadFolderButton) {
        loadFolderButton.addEventListener('click', loadFolderList);
    }

    if (startProcessingBtn) {
        startProcessingBtn.addEventListener('click', startProcessing);
    }

    if (saveToMinioBtn) {
        saveToMinioBtn.addEventListener('click', saveToMinio);
    }
    // Lắng nghe sự kiện click cho nút "Chọn file khác"
    const resetUploadBtn = document.querySelector('.btn-reset-upload'); 
    if (resetUploadBtn) {
        resetUploadBtn.addEventListener('click', resetUpload);
    }
    // THÊM: Event listener cho nút chọn folder
    if (chooseFolderButton) {
        chooseFolderButton.addEventListener('click', () => {
            if (folderInput) folderInput.value = '';
            if (folderInput) folderInput.click();
        });
    }
    // THÊM: Event listener cho folder input
    if (folderInput) {
        folderInput.addEventListener('change', handleFolderSelection);
    }

    // THÊM: Event listeners cho folder navigation
    if (prevFileBtn) {
        prevFileBtn.addEventListener('click', () => navigateFolderFile(-1));
    }
    if (nextFileBtn) {
        nextFileBtn.addEventListener('click', () => navigateFolderFile(1));
    }
    if (saveAllToMinioBtn) {
        saveAllToMinioBtn.addEventListener('click', saveAllFolderFilesToMinio);
    }
}


// THÊM: Hàm xử lý chọn folder
function handleFolderSelection(e) {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
        // Lọc chỉ lấy file có extension hỗ trợ
        const supportedFiles = files.filter(file => {
            const ext = file.name.toLowerCase().split('.').pop();
            return ['pdf', 'docx', 'pptx', 'txt'].includes(ext);
        });

        if (supportedFiles.length === 0) {
            alert('Không tìm thấy file hỗ trợ trong folder. Hỗ trợ: PDF, DOCX, PPTX, TXT');
            return;
        }

        folderFiles = supportedFiles;
        currentFolderFileIndex = 0;
        folderMetadataList = [];
        isProcessingFolder = true;
        selectedDataSource = 'folder-upload';

        // Hiển thị thông tin folder
        const folderPath = supportedFiles[0].webkitRelativePath.split('/')[0];
        if (folderName) folderName.textContent = folderPath;
        if (totalFiles) totalFiles.textContent = supportedFiles.length;
        if (totalFilesDisplay) totalFilesDisplay.textContent = supportedFiles.length;
        if (folderInfoBox) folderInfoBox.style.display = 'block';
        if (folderNavigationButtons) folderNavigationButtons.style.display = 'block';

        updateSourceStatus(`Đã chọn folder "${folderPath}" với ${supportedFiles.length} file(s)`);
        
        // Bắt đầu suy luận metadata cho file đầu tiên
        inferAndShowMetadataForCurrentFolderFile();
        
        // Đảm bảo Select2 của MinIO reset
        if (minioFolderSelect) $(minioFolderSelect).val(null).trigger('change');

        // HIỂN THỊ VÀ ACTIVE NÚT START NGAY LẬP TỨC KHI CHỌN FOLDER
        showStartButton();
        if (startProcessingBtn) {
            startProcessingBtn.disabled = false;
        }

    } else {
        console.log("Người dùng không chọn folder nào.");
        if (!selectedDataSource || selectedDataSource === 'folder-upload') {
            resetUpload(); 
        }
    }
}

// THÊM: Hàm suy luận metadata cho file hiện tại trong folder
// THÊM: Hàm suy luận metadata cho file hiện tại trong folder
async function inferAndShowMetadataForCurrentFolderFile() {
    if (currentFolderFileIndex >= folderFiles.length) return;

    const currentFile = folderFiles[currentFolderFileIndex];
    
    // Cập nhật thông tin file hiện tại
    if (currentFileIndex) currentFileIndex.textContent = currentFolderFileIndex + 1;
    
    // Ẩn upload option và hiển thị metadata box
    const uploadOption = document.getElementById('uploadOption');
    if (uploadOption) uploadOption.style.display = 'none';
    if (metadataPreviewBox) metadataPreviewBox.style.display = 'block';

    // Cập nhật nút navigation
    if (prevFileBtn) prevFileBtn.disabled = currentFolderFileIndex === 0;
    if (nextFileBtn) nextFileBtn.disabled = currentFolderFileIndex === folderFiles.length - 1;

    // Kiểm tra nếu metadata đã được suy luận cho file này
    if (folderMetadataList[currentFolderFileIndex]) {
        displayMetadata(folderMetadataList[currentFolderFileIndex].metadata, currentFile);
        
        // SỬA: THÊM dòng này để hiển thị nút save cho file đã có metadata
        showSaveButtonsForFolder();
        return;
    }

    // Hiển thị trạng thái đang suy luận
    const metaFilename = document.getElementById('metaFilename');
    const metaSubject = document.getElementById('metaSubject');
    const metaType = document.getElementById('metaType');
    const metaLevel = document.getElementById('metaLevel');
    const metaPages = document.getElementById('metaPages');

    if (metaFilename) metaFilename.textContent = currentFile.name;
    if (metaSubject) metaSubject.textContent = 'Đang suy luận...';
    if (metaType) metaType.textContent = 'Đang suy luận...';
    if (metaLevel) metaLevel.textContent = 'Đang suy luận...';
    if (metaPages) metaPages.textContent = 'Đang suy luận...';
    
    if (saveToMinioBtn) saveToMinioBtn.style.display = 'none';
    if (saveAllToMinioBtn) saveAllToMinioBtn.style.display = 'none';

    const formData = new FormData();
    formData.append('file', currentFile);

    try {
        const response = await fetch('/infer-metadata-only', { 
            method: 'POST',
            body: formData
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Server error: ${response.status} - ${errorData.message}`);
        }
        const metadata = await response.json();
        console.log('Metadata nhận được từ server:', metadata);

        // Lưu metadata vào danh sách
        folderMetadataList[currentFolderFileIndex] = {
            metadata: metadata,
            file: currentFile
        };

        displayMetadata(metadata, currentFile);
        
        // Hiển thị nút save sau khi metadata hoàn thành
        showSaveButtonsForFolder();

    } catch (error) {
        console.error('Lỗi khi suy luận metadata:', error);
        alert('Lỗi khi suy luận metadata: ' + error.message);
        if (metaSubject) metaSubject.textContent = 'Lỗi!';
        if (metaType) metaType.textContent = 'Lỗi!';
        if (metaLevel) metaLevel.textContent = 'Lỗi!';
        if (metaPages) metaPages.textContent = 'Lỗi!';
    }
}
// THÊM: Hàm hiển thị metadata
// THÊM: Hàm hiển thị metadata
function displayMetadata(metadata, file) {
    const metaFilename = document.getElementById('metaFilename');
    const metaSubject = document.getElementById('metaSubject');
    const metaType = document.getElementById('metaType');
    const metaLevel = document.getElementById('metaLevel');
    const metaPages = document.getElementById('metaPages');

    // SỬA: Kiểm tra xem metadata có phải là object bọc ngoài không
    const actualMetadata = metadata.metadata || metadata;

    if (metaFilename) metaFilename.textContent = actualMetadata.original_filename || file.name;
    if (metaSubject) metaSubject.textContent = actualMetadata.gpt_subject_raw || 'Không xác định';
    if (metaType) metaType.textContent = actualMetadata.gpt_content_type_raw || 'Không xác định';
    if (metaLevel) metaLevel.textContent = actualMetadata.gpt_educational_level_raw || 'Không xác định';
    if (metaPages) metaPages.textContent = actualMetadata.pages_count || 'Không xác định';
}

// THÊM: Hàm điều hướng trong folder
function navigateFolderFile(direction) {
    const newIndex = currentFolderFileIndex + direction;
    if (newIndex >= 0 && newIndex < folderFiles.length) {
        currentFolderFileIndex = newIndex;
        inferAndShowMetadataForCurrentFolderFile();
    }
}

// THÊM: Hàm hiển thị nút save cho folder
function showSaveButtonsForFolder() {
    if (saveToMinioBtn) {
        saveToMinioBtn.style.display = 'inline-flex';
        saveToMinioBtn.disabled = false;
        saveToMinioBtn.innerHTML = '<i class="fas fa-save"></i> Lưu file này';
    }
    if (saveAllToMinioBtn) {
        saveAllToMinioBtn.style.display = 'inline-flex';
        saveAllToMinioBtn.disabled = false;
        saveAllToMinioBtn.innerHTML = '<i class="fas fa-save"></i> Lưu tất cả vào MinIO';
    }
}

// THÊM: Hàm lưu tất cả file trong folder vào MinIO
async function saveAllFolderFilesToMinio() {
    if (folderFiles.length === 0) {
        alert('Không có file nào để lưu!');
        return;
    }

    if (saveAllToMinioBtn) {
        saveAllToMinioBtn.disabled = true;
        saveAllToMinioBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang lưu tất cả...';
    }

    let successCount = 0;
    let failCount = 0;
    const failedFiles = [];

    for (let i = 0; i < folderFiles.length; i++) {
        try {
            // Nếu chưa có metadata cho file này, suy luận trước
            if (!folderMetadataList[i]) {
                currentFolderFileIndex = i;
                await inferMetadataForFile(folderFiles[i], i);
            }

            if (folderMetadataList[i]) {
                await saveFileToMinio(folderMetadataList[i].file, folderMetadataList[i].metadata);
                successCount++;
            } else {
                failCount++;
                failedFiles.push(folderFiles[i].name);
            }
        } catch (error) {
            console.error(`Lỗi khi lưu file ${folderFiles[i].name}:`, error);
            failCount++;
            failedFiles.push(folderFiles[i].name);
        }
    }

    // Cập nhật selectedDataSource và minioFilesToProcess
    selectedDataSource = 'minio-saved-folder';
    minioFilesToProcess = folderMetadataList.map(item => ({
        name: item.metadata.original_filename,
        object_name: generateObjectName(item.metadata)
    }));

    // Hiển thị kết quả
    let message = `Đã lưu ${successCount}/${folderFiles.length} file thành công`;
    if (failCount > 0) {
        message += `\nFile lỗi: ${failedFiles.join(', ')}`;
    }
    alert(message);

    // Cập nhật UI
    if (startProcessingBtn) {
        startProcessingBtn.classList.remove('btn-secondary');
        startProcessingBtn.classList.add('btn-primary');
        startProcessingBtn.disabled = false;
        startProcessingBtn.style.display = 'inline-flex';
    }
    updateSourceStatus(`Đã lưu ${successCount} file từ folder vào MinIO. Sẵn sàng để xử lý.`);

    // Ẩn metadata preview
    if (metadataPreviewBox) metadataPreviewBox.style.display = 'none';
    
    // Hiển thị lại upload option
    const uploadOption = document.getElementById('uploadOption');
    if (uploadOption) uploadOption.style.display = 'block';

    if (saveAllToMinioBtn) {
        saveAllToMinioBtn.disabled = false;
        saveAllToMinioBtn.innerHTML = '<i class="fas fa-save"></i> Lưu tất cả vào MinIO';
    }
}

// THÊM: Hàm suy luận metadata cho file cụ thể (không hiển thị UI)
async function inferMetadataForFile(file, index) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/infer-metadata-only', { 
            method: 'POST',
            body: formData
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Server error: ${response.status} - ${errorData.message}`);
        }
        const metadata = await response.json();
        
        folderMetadataList[index] = {
            metadata: metadata,
            file: file
        };
        
        return metadata;
    } catch (error) {
        console.error(`Lỗi khi suy luận metadata cho file ${file.name}:`, error);
        throw error;
    }
}

// THÊM: Hàm tạo object name cho MinIO
function generateObjectName(metadata) {
    const level_path = metadata.gpt_educational_level || "khac";
    const subject_path = metadata.gpt_subject || "tong-hop";
    const doc_type_path = metadata.gpt_content_type || "tai-lieu-khac";
    const original_filename = metadata.original_filename;
    return `${level_path}/${subject_path}/${doc_type_path}/${original_filename}`;
}

// THÊM: Hàm lưu file đơn lẻ vào MinIO
async function saveFileToMinio(file, metadata) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('metadata', JSON.stringify(metadata));

    const response = await fetch('/save-to-minio', {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`Server error: ${response.status} - ${errorData.message}`);
    }
    
    const result = await response.json();
    if (result.status !== 'success') {
        throw new Error(result.message || 'Lỗi không xác định khi lưu file');
    }
    
    return result;
}

// Hide/Show main sections
function hideInitialForms() {
    if (defaultMessage) defaultMessage.style.display = 'none';
}

function showInitialForms() {
    if (dataSourceContainer) dataSourceContainer.style.display = 'block';
    if (defaultMessage) defaultMessage.style.display = 'block';
}

function showProcessingSection() {
    if (processingSection) {
        processingSection.style.display = 'block';
        processingSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// --- File selection (CẬP NHẬT TRỌNG TÂM)
// SỬA: Cập nhật handleFileSelection để reset folder data
function handleFileSelection(e) {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
        selectedFiles = files;
        selectedDataSource = 'upload';
        isProcessingFolder = false; // Reset folder flag
        folderFiles = []; // Reset folder data
        folderMetadataList = [];
        
        updateSourceStatus(`Đã chọn ${files.length} file(s) từ máy tính`);
        inferAndShowMetadata(files[0]);
        
        // Ẩn thông tin folder nếu có
        if (folderInfoBox) folderInfoBox.style.display = 'none';
        if (folderNavigationButtons) folderNavigationButtons.style.display = 'none';
        
        if (minioFolderSelect) $(minioFolderSelect).val(null).trigger('change');
        showStartButton(); 
        if (startProcessingBtn) startProcessingBtn.disabled = false;
    } else {
        if (!selectedDataSource || selectedDataSource === 'upload') {
            resetUpload(); 
        }
    }
}

function handleFileDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    fileDropZone.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
        selectedFiles = files;
        selectedDataSource = 'upload';
        isProcessingFolder = false; // Reset folder flag
        folderFiles = []; // Reset folder data
        folderMetadataList = [];
        
        updateSourceStatus(`Đã chọn ${files.length} file(s) qua drag & drop`);
        inferAndShowMetadata(files[0]);
        
        // Ẩn thông tin folder nếu có
        if (folderInfoBox) folderInfoBox.style.display = 'none';
        if (folderNavigationButtons) folderNavigationButtons.style.display = 'none';
        
        if (minioFolderSelect) $(minioFolderSelect).val(null).trigger('change');
        showStartButton();
        if (startProcessingBtn) startProcessingBtn.disabled = false;
    }
}

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    fileDropZone.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    fileDropZone.classList.remove('dragover');
}

// --- Metadata Preview (CẬP NHẬT)
async function inferAndShowMetadata(file) {
    const uploadOption = document.getElementById('uploadOption');
    if (uploadOption) {
        uploadOption.style.display = 'none';
    }
    if (metadataPreviewBox) {
        metadataPreviewBox.style.display = 'block';
    }
    const metaFilename = document.getElementById('metaFilename');
    const metaSubject = document.getElementById('metaSubject');
    const metaType = document.getElementById('metaType');
    const metaLevel = document.getElementById('metaLevel');
    const metaPages = document.getElementById('metaPages');

    if (metaFilename) metaFilename.textContent = file.name;
    if (metaSubject) metaSubject.textContent = 'Đang suy luận...';
    if (metaType) metaType.textContent = 'Đang suy luận...';
    if (metaLevel) metaLevel.textContent = 'Đang suy luận...';
    if (metaPages) metaPages.textContent = 'Đang suy luận...';
    if (saveToMinioBtn) saveToMinioBtn.style.display = 'none'; // Ẩn nút save khi đang suy luận
    // Nút startProcessingBtn đã được active ở handleFileSelection/Drop, không cần ẩn lại

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/infer-metadata-only', { 
            method: 'POST',
            body: formData
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Server error: ${response.status} - ${errorData.message}`);
        }
        const metadata = await response.json();
        console.log('Metadata nhận được từ server:', metadata);

        // LƯU METADATA VÀO BIẾN GLOBAL
        currentFileMetadata = {
            metadata: metadata,
            file: file
        };

        if (metaFilename) metaFilename.textContent = metadata.original_filename || file.name;
        if (metaSubject) metaSubject.textContent = metadata.gpt_subject_raw || 'Không xác định';
        if (metaType) metaType.textContent = metadata.gpt_content_type_raw || 'Không xác định';
        if (metaLevel) metaLevel.textContent = metadata.gpt_educational_level_raw || 'Không xác định';
        if (metaPages) metaPages.textContent = metadata.pages_count || 'Không xác định';

        // HIỂN THỊ NÚT SAVE SAU KHI METADATA HOÀN THÀNH
        showSaveButton();

    } catch (error) {
        console.error('Lỗi khi suy luận metadata:', error);
        alert('Lỗi khi suy luận metadata: ' + error.message + '\nVui lòng kiểm tra console để biết thêm chi tiết.');
        if (metaSubject) metaSubject.textContent = 'Lỗi!';
        if (metaType) metaType.textContent = 'Lỗi!';
        if (metaLevel) metaLevel.textContent = 'Lỗi!';
        if (metaPages) metaPages.textContent = 'Lỗi!';
        if (saveToMinioBtn) saveToMinioBtn.style.display = 'none';
        
        // Vẫn giữ nút Start ProcessingBtn được hiển thị nhưng có thể muốn disable nó nếu có lỗi metadata
        // Tuy nhiên theo ý bố, nút Start chỉ chạy sau khi Save To MinIO, nên ta không cần disable nó ở đây.
    }
}

// THÊM HÀM HIỂN THỊ NÚT SAVE
function showSaveButton() {
    if (saveToMinioBtn) {
        saveToMinioBtn.style.display = 'inline-flex';
        saveToMinioBtn.disabled = false;
        saveToMinioBtn.innerHTML = '<i class="fas fa-save"></i> Lưu vào MinIO';
    }
}

// THÊM HÀM XỬ LÝ SAVE TO MINIO
async function saveToMinio() {

    // Nếu đang xử lý folder, lưu file hiện tại
    if (isProcessingFolder && folderMetadataList[currentFolderFileIndex]) {
        const currentFileData = folderMetadataList[currentFolderFileIndex];
        if (!currentFileData || !currentFileData.file || !currentFileData.metadata) {
            alert('Không có file hoặc metadata để lưu!');
            return;
        }
        
        if (saveToMinioBtn) {
            saveToMinioBtn.disabled = true;
            saveToMinioBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang lưu...';
        }

        try {
            await saveFileToMinio(currentFileData.file, currentFileData.metadata);
            alert(`Đã lưu file "${currentFileData.file.name}" thành công vào MinIO!`);
        } catch (error) {
            console.error('Lỗi khi lưu file vào MinIO:', error);
            alert('Lỗi khi lưu file vào MinIO: ' + error.message);
        } finally {
            if (saveToMinioBtn) {
                saveToMinioBtn.disabled = false;
                saveToMinioBtn.innerHTML = '<i class="fas fa-save"></i> Lưu file này';
            }
        }
        return;
    }
    if (!currentFileMetadata || !currentFileMetadata.file || !currentFileMetadata.metadata) {
        alert('Không có file hoặc metadata để lưu!');
        return;
    }
    
    if (saveToMinioBtn) {
        saveToMinioBtn.disabled = true;
        saveToMinioBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang lưu...';
    }

    const formData = new FormData();
    formData.append('file', currentFileMetadata.file);
    formData.append('metadata', JSON.stringify(currentFileMetadata.metadata));

    try {
        const response = await fetch('/save-to-minio', {
            method: 'POST',
            body: formData
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Server error: ${response.status} - ${errorData.message}`);
        }
        const result = await response.json();
        console.log('Kết quả lưu MinIO:', result);
        if (result.status === 'success') {
            alert('Đã lưu file thành công vào MinIO!');
            
            selectedDataSource = 'minio-saved-file'; // Đánh dấu là file đã lưu vào minio
            minioFilesToProcess = [{
                name: currentFileMetadata.metadata.original_filename,
                object_name: result.object_name // Đảm bảo backend trả về object_name
            }];
            // Nút "Bắt đầu xử lý" đã sáng từ khi chọn file, không cần gọi showStartButton() lại
            // Chỉ cần đảm bảo nó vẫn đang ở trạng thái active (màu tím)
            if (startProcessingBtn) {
                startProcessingBtn.classList.remove('btn-secondary');
                startProcessingBtn.classList.add('btn-primary');
                startProcessingBtn.disabled = false;
                startProcessingBtn.style.display = 'inline-flex'; // Đảm bảo nó hiển thị
            }
            updateSourceStatus(`Đã lưu file: "${minioFilesToProcess[0].name}" vào MinIO. Sẵn sàng để xử lý.`);
            
            // Ẩn metadata preview và nút save sau khi lưu
            if (metadataPreviewBox) metadataPreviewBox.style.display = 'none';
            if (saveToMinioBtn) saveToMinioBtn.style.display = 'none';

            // HIỂN THỊ LẠI KHUNG TẢI FILE MỚI LÊN (nếu muốn cho phép tải tiếp)
            const uploadOption = document.getElementById('uploadOption');
            if (uploadOption) {
                uploadOption.style.display = 'block';
            }
            // Clear the file input for a new upload
            if (fileInput) fileInput.value = '';

        } else {
            throw new Error(result.message || 'Lỗi không xác định khi lưu file');
        }

    } catch (error) {
        console.error('Lỗi khi lưu file vào MinIO:', error);
        alert('Lỗi khi lưu file vào MinIO: ' + error.message);
    } finally {
        if (saveToMinioBtn) {
            saveToMinioBtn.disabled = false;
            saveToMinioBtn.innerHTML = '<i class="fas fa-save"></i> Lưu vào MinIO';
        }
    }
}

function resetUpload() {
    selectedFiles = [];
    minioFilesToProcess = [];
    folderFiles = []; // THÊM: Reset folder data
    folderMetadataList = []; // THÊM: Reset folder metadata
    currentFolderFileIndex = 0; // THÊM: Reset folder index
    isProcessingFolder = false; // THÊM: Reset folder flag
    if (fileInput) fileInput.value = ""; // Rất quan trọng để reset giá trị input
    if (folderInput) folderInput.value = "";
    selectedDataSource = null;
    currentFileMetadata = null; // RESET METADATA

    const uploadOption = document.getElementById('uploadOption');
    if (uploadOption) {
        uploadOption.style.display = 'block';
    }
    if (metadataPreviewBox) metadataPreviewBox.style.display = 'none';
    if (saveToMinioBtn) saveToMinioBtn.style.display = 'none';
    if (startProcessingBtn) {
        startProcessingBtn.style.display = 'none'; // Ẩn nút Start
        startProcessingBtn.classList.remove('btn-primary'); // Xóa màu active
        startProcessingBtn.classList.add('btn-secondary'); // Đặt lại màu xám
        startProcessingBtn.disabled = true; // Vô hiệu hóa nút
    }
    if (saveAllToMinioBtn) saveAllToMinioBtn.style.display = 'none';
    if (sourceStatus) sourceStatus.style.display = 'none';
    if (folderInfoBox) folderInfoBox.style.display = 'none'; // THÊM
    if (folderNavigationButtons) folderNavigationButtons.style.display = 'none'; // THÊM
    // Reset progress steps
    resetProgressSteps();
    // Ẩn kết quả cuối cùng
    if (finalResults) finalResults.style.display = 'none';

    // Reset Select2 selection
    if (minioFolderSelect) {
        $(minioFolderSelect).val(null).trigger('change');
    }

    // Reset simulated results
    simulatedTotalFilesProcessed = 0;
    simulatedSuccessfullyDownloadedFiles = 0;
    simulatedFailedDownloadFiles = [];
    simulatedTotalChunksGenerated = 0;
    simulatedTotalProcessingTimeMs = 0;
    simulatedProcessStartTime = null;

    // Ẩn khung processing
    if (processingSection) processingSection.style.display = 'none';
    showInitialForms(); // Đảm bảo defaultMessage hiển thị lại nếu cần
}

// --- Folder from MinIO
// Đổi tên hàm cho MinIO selection
// Hàm cho MinIO folder selection (đổi tên để tránh trùng)
function handleMinioFolderSelection(e) {
    const selectedValue = $(this).val();
    if (selectedValue) {
        selectedDataSource = 'minio';
        // Reset folder upload data
        isProcessingFolder = false;
        folderFiles = [];
        folderMetadataList = [];
        currentFolderFileIndex = 0;
        
        updateSourceStatus(`Đã chọn folder: ${selectedValue}`);
        showStartButton();
        
        // Ẩn thông tin folder upload nếu có
        if (folderInfoBox) folderInfoBox.style.display = 'none';
        if (folderNavigationButtons) folderNavigationButtons.style.display = 'none';
        if (metadataPreviewBox) metadataPreviewBox.style.display = 'none';
        if (saveToMinioBtn) saveToMinioBtn.style.display = 'none';
        if (saveAllToMinioBtn) saveAllToMinioBtn.style.display = 'none';
        
        // Đảm bảo phần upload file reset
        const uploadOption = document.getElementById('uploadOption');
        if (uploadOption) uploadOption.style.display = 'block';
        if (fileInput) fileInput.value = '';
        if (folderInput) folderInput.value = ''; // THÊM dòng này
        selectedFiles = [];
        currentFileMetadata = null;
    } else {
        selectedDataSource = null;
        updateSourceStatus(`Chưa chọn folder từ MinIO`);
        if (startProcessingBtn) {
            startProcessingBtn.style.display = 'none';
            startProcessingBtn.classList.remove('btn-primary');
            startProcessingBtn.classList.add('btn-secondary');
            startProcessingBtn.disabled = true;
        }
        if (defaultMessage) defaultMessage.style.display = 'block';
        minioFilesToProcess = [];
    }
    // Ẩn khung processing và kết quả khi thay đổi lựa chọn nguồn
    if (processingSection) processingSection.style.display = 'none';
    if (finalResults) finalResults.style.display = 'none';
    resetProgressSteps();
}

// Và update trong initializeEventListeners:
if (minioFolderSelect) {
    $(minioFolderSelect).on('change', handleMinioFolderSelection); // SỬA TÊN HÀM
}
function loadFolderList() {
    if (loadFolderButton) {
        loadFolderButton.disabled = true;
        loadFolderButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang tải...';
    }

    fetch('/api/minio-folders')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            const newOptions = [{ id: '', text: '-- Chọn folder --' }];
            if (data.status === 'success' && data.folders.length > 0) {
                data.folders.forEach(folder => {
                    newOptions.push({
                        id: folder,
                        text: folder.endsWith('/') ? folder.slice(0, -1) : folder
                    });
                });
                console.log('Folders loaded:', data.folders);
            } else {
                console.log('No folders found in MinIO bucket.');
            }

            $(minioFolderSelect).empty().select2({
                placeholder: "-- Chọn folder --",
                allowClear: true,
                data: newOptions,
                templateResult: formatFolderOption,
                templateSelection: formatFolderOption
            });
        })
        .catch(error => {
            console.error('There was a problem with the fetch operation:', error);
            alert('Không thể kết nối đến server hoặc có lỗi xảy ra khi tải folder.');
        })
        .finally(() => {
            if (loadFolderButton) {
                loadFolderButton.disabled = false;
                loadFolderButton.innerHTML = '<i class="fas fa-sync-alt"></i> Tải danh sách folder';
            }
        });
}

// --- UI update
function updateSourceStatus(message) {
    if (sourceInfo) sourceInfo.textContent = message;
    if (sourceStatus) sourceStatus.style.display = 'block';
}

// Hàm này dùng để cập nhật text trong các bước xử lý (stepBox)
function updateStepDescription(stepId, message) {
    const stepElement = document.getElementById(stepId);
    if (stepElement) {
        const description = stepElement.querySelector('.step-description');
        if (description) description.textContent = message;
    }
}

function showStartButton() {
    if (startProcessingBtn) {
        startProcessingBtn.style.display = 'inline-flex';
        // Đảm bảo nút được kích hoạt và có màu tím
        startProcessingBtn.classList.remove('btn-secondary');
        startProcessingBtn.classList.add('btn-primary');
        startProcessingBtn.disabled = false; // Kích hoạt nút
    }
    if (defaultMessage) defaultMessage.style.display = 'none'; // Ẩn tin nhắn mặc định khi nút start hiện ra
    if (finalResults) finalResults.style.display = 'none'; // Đảm bảo kết quả cũ ẩn
    resetProgressSteps();
}

function resetProgressSteps() {
    const steps = ['stepBox1', 'stepBox2', 'stepBox3', 'stepBox4', 'stepBox5'];
    const arrows = ['arrow1', 'arrow2', 'arrow3', 'arrow4'];

    steps.forEach(stepId => {
        const step = document.getElementById(stepId);
        if (step) {
            step.className = 'progress-step-box pending';
            const description = step.querySelector('.step-description');
            if (description) description.textContent = 'Đang chờ...';
        }
    });

    arrows.forEach(arrowId => {
        const arrow = document.getElementById(arrowId);
        if (arrow) arrow.className = 'progress-arrow';
    });

    if (loadDataDescription) {
        loadDataDescription.textContent = 'Đang chờ...';
    }
    
    // Reset vector database info
    window.vectorDatabaseInfo = null;
}
// THÊM: Lưu vector database info vào global variable
function storeVectorDatabaseInfo(vectorDbInfo) {
    if (vectorDbInfo) {
        window.vectorDatabaseInfo = vectorDbInfo;
        console.log('Stored vector database info:', vectorDbInfo);
    }
}
// --- Processing (MAIN LOGIC) ---
async function startProcessing() {
    // Điều kiện để bắt đầu xử lý
    if (selectedDataSource === 'upload' && !currentFileMetadata) {
        alert('Vui lòng đợi quá trình suy luận metadata hoàn tất và lưu file vào MinIO trước khi xử lý.');
        return;
    }
    // Kiểm tra cho folder upload
    if (selectedDataSource === 'folder-upload' && folderMetadataList.length === 0) {
        alert('Vui lòng đợi quá trình suy luận metadata hoàn tất và lưu tất cả file vào MinIO trước khi xử lý.');
        return;
    }

    if (!selectedDataSource) {
        alert('Vui lòng chọn nguồn dữ liệu trước khi bắt đầu xử lý!');
        return;
    }

    // Reset simulated results for a new run
    simulatedTotalFilesProcessed = 0;
    simulatedSuccessfullyDownloadedFiles = 0;
    simulatedFailedDownloadFiles = [];
    simulatedTotalChunksGenerated = 0;
    simulatedTotalProcessingTimeMs = 0;
    simulatedProcessStartTime = Date.now();

    showProcessingSection();
    if (startProcessingBtn) {
        startProcessingBtn.style.display = 'none';
        startProcessingBtn.classList.remove('btn-primary');
        startProcessingBtn.classList.add('btn-secondary');
        startProcessingBtn.disabled = true;
    }
    if (finalResults) finalResults.style.display = 'none';
    resetProgressSteps();

    // Set initial text for step 1 detailed log
    if (loadDataDescription) loadDataDescription.textContent = 'Đang khởi tạo quá trình tải file...';

    try {
        if (selectedDataSource === 'minio') {
            const selectedFolder = $(minioFolderSelect).val();
            if (!selectedFolder) {
                alert('Vui lòng chọn một folder MinIO hợp lệ.');
                return;
            }
            await loadMinIOFiles(selectedFolder);
        } else if (selectedDataSource === 'minio-saved-file') {
            if (minioFilesToProcess.length === 0) {
                alert('Không tìm thấy thông tin file đã lưu để xử lý.');
                return;
            }
            console.log("Processing a single file recently saved to MinIO:", minioFilesToProcess[0].name);
            
            // SỬA: Gọi real pipeline thay vì downloadMinioFile
            await processFileWithRealPipeline(minioFilesToProcess[0].object_name);
            
        } else if (selectedDataSource === 'minio-saved-folder') {
            if (minioFilesToProcess.length === 0) {
                alert('Không tìm thấy thông tin folder đã lưu để xử lý.');
                return;
            }
            console.log(`Processing ${minioFilesToProcess.length} files from saved folder`);
            
            // SỬA: Chọn file đại diện và chạy pipeline
            if (minioFilesToProcess.length > 0) {
                const representativeFile = minioFilesToProcess[0].object_name;
                await processFileWithRealPipeline(representativeFile);
            }
        } else {
            alert('Nguồn dữ liệu không hợp lệ hoặc chưa sẵn sàng để xử lý. Vui lòng thử lại.');
            return;
        }

    } catch (error) {
        console.error("Lỗi trong quá trình xử lý:", error);
        if (stepBox1) {
            stepBox1.classList.remove('active', 'in-progress', 'completed');
            stepBox1.classList.add('error');
            const description = stepBox1.querySelector('.step-description');
            if (description) description.textContent = `Lỗi tải: ${error.message || 'Không xác định'}`;
        }
        if (arrow1) arrow1.className = 'progress-arrow error';
        showFinalResults(false);
    }
}


// THÊM: Hàm mới để xử lý single file với real pipeline
async function processFileWithRealPipeline(objectName) {
    console.log(`🚀 Processing single file with real pipeline: ${objectName}`);
    
    // Step 1: Mark as active
    if (stepBox1) {
        stepBox1.classList.remove('pending');
        stepBox1.classList.add('active');
    }
    if (arrow1) arrow1.classList.add('active');
    if (loadDataDescription) {
        loadDataDescription.textContent = `Chuẩn bị xử lý file: ${objectName.split('/').pop()}`;
    }
    
    // Step 1: Complete immediately for single file
    simulatedTotalFilesProcessed = 1;
    simulatedSuccessfullyDownloadedFiles = 1;
    
    if (loadDataDescription) {
        loadDataDescription.textContent = `✅ Đã chuẩn bị file: ${objectName.split('/').pop()}`;
    }
    if (stepBox1) {
        stepBox1.classList.remove('active');
        stepBox1.classList.add('completed');
    }
    if (arrow1) arrow1.classList.add('completed');
    
    // Bắt đầu real pipeline processing
    await startRealPipelineProcessing(objectName);
}

// ORIGINAL FUNCTION: Load files from MinIO folder
// UPDATED FUNCTION: Load files from MinIO folder và chạy pipeline
async function loadMinIOFiles(folderPrefix) {
    if (loadDataDescription) loadDataDescription.textContent = 'Đang tải danh sách file từ MinIO...';
    if (stepBox1) {
        stepBox1.classList.remove('pending');
        stepBox1.classList.add('active');
    }
    if (arrow1) arrow1.classList.add('active');

    simulatedSuccessfullyDownloadedFiles = 0;
    simulatedFailedDownloadFiles = [];

    try {
        // 1. Lấy danh sách file từ MinIO
        const response = await fetch(`/api/minio-files?prefix=${encodeURIComponent(folderPrefix)}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Server error: ${response.status} - ${errorData.message}`);
        }
        const data = await response.json();

        simulatedTotalFilesProcessed = data.files.length;

        if (data.status === 'success' && data.files.length > 0) {
            minioFilesToProcess = data.files;
            console.log(`Found ${minioFilesToProcess.length} files in MinIO folder '${folderPrefix}'.`);

            // 2. Lấy file đại diện để xử lý pipeline
            if (loadDataDescription) {
                loadDataDescription.textContent += `\n🔍 Tìm file đại diện để xử lý...`;
            }

            const repFileResponse = await fetch('/api/get-representative-file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ folder_prefix: folderPrefix })
            });

            if (repFileResponse.ok) {
                const repFileData = await repFileResponse.json();
                if (repFileData.success) {
                    representativeFile = repFileData.representative_file;
                    
                    if (loadDataDescription) {
                        loadDataDescription.textContent += `\n📄 File đại diện: ${repFileData.file_name}`;
                        loadDataDescription.textContent += `\n🚀 Bắt đầu pipeline processing...`;
                    }

                    // 3. Hoàn thành step 1
                    simulatedSuccessfullyDownloadedFiles = minioFilesToProcess.length;
                    let finalMessage = `Đã tải tất cả ${simulatedSuccessfullyDownloadedFiles} file từ MinIO.`;
                    
                    updateStepDescription('stepBox1', finalMessage);
                    if (stepBox1) {
                        stepBox1.classList.remove('active');
                        stepBox1.classList.add('completed');
                    }
                    if (arrow1) arrow1.classList.add('completed');

                    // 4. Bắt đầu pipeline với file đại diện
                    await startRealPipelineProcessing(representativeFile);
                    
                } else {
                    throw new Error("Không tìm thấy file hỗ trợ để xử lý");
                }
            } else {
                throw new Error("Không thể lấy file đại diện");
            }

        } else {
            minioFilesToProcess = [];
            simulatedTotalFilesProcessed = 0;
            simulatedSuccessfullyDownloadedFiles = 0;
            if (loadDataDescription) loadDataDescription.textContent = 'Không tìm thấy file nào trong folder MinIO.';
            if (stepBox1) {
                stepBox1.classList.remove('active');
                stepBox1.classList.add('completed-with-warnings');
            }
            if (arrow1) arrow1.classList.add('completed');
            console.warn('Không có file để xử lý trong folder đã chọn.');
            
            // Vẫn hiển thị final results ngay cả khi không có file
            showFinalResults(true);
        }
    } catch (error) {
        console.error('Lỗi khi tải danh sách file hoặc xử lý pipeline từ MinIO:', error);
        if (loadDataDescription) loadDataDescription.textContent = `Lỗi: ${error.message}`;
        if (stepBox1) {
            stepBox1.classList.remove('active');
            stepBox1.classList.add('error');
        }
        if (arrow1) arrow1.classList.add('error');
        showFinalResults(false);
        throw error;
    }
}

// ORIGINAL FUNCTION: Download a single file from MinIO
async function downloadMinioFile(objectName, fileName, currentCount, totalCount) {
    const currentLogLine = `Đang tải: ${fileName} (${currentCount}/${totalCount})\n`;
    if (loadDataDescription) {
        loadDataDescription.textContent += currentLogLine;
        loadDataDescription.scrollTop = loadDataDescription.scrollHeight;
    }

    try {
        const response = await fetch('/api/download-minio-file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ object_name: objectName })
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Server error: ${response.status} - ${errorData.message}`);
        }
        const result = await response.json();
        if (result.status !== 'success') {
            throw new Error(result.message);
        }
        console.log(`Đã tải file ${fileName} về: ${result.local_path}`);

        if (loadDataDescription) {
            loadDataDescription.textContent = loadDataDescription.textContent.replace(
                currentLogLine.trim(),
                `✅ Đã tải: ${fileName}`
            ) + '\n';
            loadDataDescription.scrollTop = loadDataDescription.scrollHeight;
        }

    } catch (error) {
        console.error(`Lỗi khi tải file ${fileName}:`, error);
        if (loadDataDescription) {
            loadDataDescription.textContent = loadDataDescription.textContent.replace(
                currentLogLine.trim(),
                `❌ Lỗi tải ${fileName}: ${error.message}`
            ) + '\n';
            loadDataDescription.scrollTop = loadDataDescription.scrollHeight;
        }
        throw error;
    }
}

// HÀM NÀY 
// THÊM: Hàm mới để chạy real pipeline processing
// THÊM: Cập nhật startRealPipelineProcessing để lưu vector database info
async function startRealPipelineProcessing(objectName) {
    console.log(`🚀 Starting real pipeline processing for: ${objectName}`);
    
    // Close any existing event source
    if (pipelineEventSource) {
        pipelineEventSource.close();
    }

    // Reset vector database info
    window.vectorDatabaseInfo = null;

    // Sử dụng SSE để nhận progress real-time
    try {
        const response = await fetch('/api/process-pipeline-stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ object_name: objectName })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        // THÊM: Lưu vector database info nếu có
                        if (data.results && data.results.vector_database) {
                            storeVectorDatabaseInfo(data.results.vector_database);
                        }
                        
                        handlePipelineProgress(data);
                    } catch (e) {
                        console.error('Error parsing SSE data:', e);
                    }
                }
            }
        }

    } catch (error) {
        console.error('Error in pipeline processing:', error);
        // Handle error - mark current step as failed
        const activeStep = document.querySelector('.progress-step-box.active');
        if (activeStep) {
            activeStep.classList.remove('active');
            activeStep.classList.add('error');
            const description = activeStep.querySelector('.step-description');
            if (description) description.textContent = `Lỗi: ${error.message}`;
        }
        showFinalResults(false);
    }
}


// THÊM: Hàm xử lý progress từ pipeline
function handlePipelineProgress(data) {
    console.log('Pipeline progress:', data);

    if (data.step) {
        const stepId = `stepBox${data.step}`;
        const stepElement = document.getElementById(stepId);
        const arrowId = `arrow${data.step}`;
        const arrowElement = document.getElementById(arrowId);

        if (stepElement) {
            const description = stepElement.querySelector('.step-description');

            // Reset classes
            stepElement.classList.remove('pending', 'active', 'completed', 'error', 'completed-with-warnings');
            
            if (data.status === 'active') {
                stepElement.classList.add('active');
                if (description) description.textContent = data.message;
                
                if (arrowElement) {
                    arrowElement.classList.remove('pending', 'completed', 'error');
                    arrowElement.classList.add('active');
                }
                
                // Special handling cho MongoDB step
                if (data.step === 5) {
                    console.log('🗄️ MongoDB save step started');
                }
                
            } else if (data.status === 'completed') {
                stepElement.classList.add('completed');
                if (description) description.textContent = data.message;
                
                if (arrowElement) {
                    arrowElement.classList.remove('active');
                    arrowElement.classList.add('completed');
                }
                
                // Special handling cho MongoDB completion
                if (data.step === 5) {
                    console.log('✅ MongoDB save step completed successfully');
                }
                
            } else if (data.status === 'error') {
                stepElement.classList.add('error');
                if (description) description.textContent = data.message;
                
                if (arrowElement) {
                    arrowElement.classList.remove('active');
                    arrowElement.classList.add('error');
                }
                
                // Special handling cho MongoDB errors
                if (data.step === 5) {
                    console.error('❌ MongoDB save step failed:', data.message);
                }
            }
        }
    } else if (data.success !== undefined) {
        // Final result
        if (data.success) {
            // Update simulated results for final display
            if (data.results) {
                simulatedTotalChunksGenerated = data.results.total_chunks || 0;
                simulatedTotalProcessingTimeMs = (data.results.processing_time || 0) * 1000;
                simulatedSuccessfullyDownloadedFiles = simulatedTotalFilesProcessed;
                
                // ENHANCED: Lưu thông tin MongoDB với enhanced data
                if (data.results.mongodb) {
                    window.mongodbInfo = data.results.mongodb;
                    mongodbInfo = data.results.mongodb; // Backup reference
                    console.log('📊 MongoDB Info received:', data.results.mongodb);
                }
                
                // Log vector database info nếu có
                if (data.results.vector_database) {
                    window.vectorDatabaseInfo = data.results.vector_database;
                    console.log('🗂️ Vector Database Info:', data.results.vector_database);
                }
            }
            showFinalResults(true);
        } else {
            // Handle MongoDB error trong final result
            if (data.mongodb) {
                window.mongodbInfo = data.mongodb;
                mongodbInfo = data.mongodb;
            }
            showFinalResults(false);
        }
    }
}

// THÊM: Hàm helper để cleanup pipeline resources
function cleanupPipelineResources() {
    if (pipelineEventSource) {
        pipelineEventSource.close();
        pipelineEventSource = null;
    }
    representativeFile = null;
}

// UPDATED: Modify resetUpload to cleanup pipeline resources
function resetUpload() {
    selectedFiles = [];
    minioFilesToProcess = [];
    folderFiles = [];
    folderMetadataList = [];
    currentFolderFileIndex = 0;
    isProcessingFolder = false;
    
    // THÊM: Cleanup pipeline resources
    cleanupPipelineResources();
    
    if (fileInput) fileInput.value = "";
    if (folderInput) folderInput.value = "";
    selectedDataSource = null;
    currentFileMetadata = null;

    const uploadOption = document.getElementById('uploadOption');
    if (uploadOption) {
        uploadOption.style.display = 'block';
    }
    if (metadataPreviewBox) metadataPreviewBox.style.display = 'none';
    if (saveToMinioBtn) saveToMinioBtn.style.display = 'none';
    if (startProcessingBtn) {
        startProcessingBtn.style.display = 'none';
        startProcessingBtn.classList.remove('btn-primary');
        startProcessingBtn.classList.add('btn-secondary');
        startProcessingBtn.disabled = true;
    }
    if (saveAllToMinioBtn) saveAllToMinioBtn.style.display = 'none';
    if (sourceStatus) sourceStatus.style.display = 'none';
    if (folderInfoBox) folderInfoBox.style.display = 'none';
    if (folderNavigationButtons) folderNavigationButtons.style.display = 'none';
    
    resetProgressSteps();
    if (finalResults) finalResults.style.display = 'none';

    if (minioFolderSelect) {
        $(minioFolderSelect).val(null).trigger('change');
    }

    // Reset simulated results
    simulatedTotalFilesProcessed = 0;
    simulatedSuccessfullyDownloadedFiles = 0;
    simulatedFailedDownloadFiles = [];
    simulatedTotalChunksGenerated = 0;
    simulatedTotalProcessingTimeMs = 0;
    simulatedProcessStartTime = null;

    if (processingSection) processingSection.style.display = 'none';
    showInitialForms();
}

// Modified: Simulate remaining steps after files are "loaded"
// function simulateRemainingProcessing() {
//     const steps = [
//         { id: 'stepBox2', title: 'Data Extraction', processing: 'Đang trích xuất nội dung...', completed: 'Đã trích xuất nội dung' },
//         { id: 'stepBox3', title: 'Chunking', processing: 'Đang chia nhỏ dữ liệu...', completed: 'Đã chia nhỏ dữ liệu' },
//         { id: 'stepBox4', title: 'Embedding', processing: 'Đang tạo embedding...', completed: 'Đã tạo embedding' },
//         { id: 'stepBox5', title: 'Lưu DB', processing: 'Đang lưu vào database...', completed: 'Đã lưu vào database' }
//     ];

//     let currentStepIndex = 0;

//     function processNextRemainingStep() {
//         if (currentStepIndex >= steps.length) {
//             simulatedTotalProcessingTimeMs = Date.now() - simulatedProcessStartTime;
//             simulatedTotalChunksGenerated = simulatedSuccessfullyDownloadedFiles > 0
//                 ? simulatedSuccessfullyDownloadedFiles * Math.floor(Math.random() * (20 - 5 + 1) + 5)
//                 : 0;
//             showFinalResults(true); // Tất cả bước mô phỏng hoàn tất thành công
//             return;
//         }

//         const step = steps[currentStepIndex];
//         const stepElement = document.getElementById(step.id);
//         if (!stepElement) {
//             currentStepIndex++;
//             setTimeout(processNextRemainingStep, 100);
//             return;
//         }

//         const description = stepElement.querySelector('.step-description');

//         stepElement.classList.remove('pending', 'completed', 'error', 'completed-with-warnings');
//         stepElement.classList.add('active');
//         if (description) description.textContent = step.processing;

//         const arrowId = `arrow${currentStepIndex + 1}`;
//         const arrow = document.getElementById(arrowId);
//         if (arrow) {
//             arrow.classList.remove('pending', 'completed', 'error');
//             arrow.classList.add('active');
//         }

//         setTimeout(() => {
//             stepElement.classList.remove('active');
//             stepElement.classList.add('completed');
//             if (description) description.textContent = step.completed;

//             if (arrow) {
//                 arrow.classList.remove('active');
//                 arrow.classList.add('completed');
//             }

//             currentStepIndex++;
//             setTimeout(processNextRemainingStep, 500);
//         }, 2000);
//     }

//     processNextRemainingStep();
// }


// MODIFIED FUNCTION: showFinalResults to use box layout
function showFinalResults(isSuccess) {
    if (finalResults) {
        finalResults.style.display = 'block';
        if (defaultMessage) defaultMessage.style.display = 'none';

        let resultsHtml = `<h4 class="mb-3">${isSuccess ? '✅ Quá trình xử lý hoàn tất!' : '❌ Quá trình xử lý thất bại!'}</h4>`;

        const totalTimeSeconds = (simulatedTotalProcessingTimeMs / 1000).toFixed(2);

        // Main statistics grid
        resultsHtml += `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
                <div style="background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,.1);">
                    <strong>Files xử lý</strong><br>
                    <span style="color: #28a745; font-size: 1.2em;">${simulatedTotalFilesProcessed}</span>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,.1);">
                    <strong>File tải thành công</strong><br>
                    <span style="color: #007bff; font-size: 1.2em;">${simulatedSuccessfullyDownloadedFiles}</span>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,.1);">
                    <strong>File lỗi tải</strong><br>
                    <span style="color: #e74c3c; font-size: 1.2em;">${simulatedFailedDownloadFiles.length}</span>
                </div>
        `;

        if (isSuccess && simulatedTotalFilesProcessed > 0) {
            resultsHtml += `
                <div style="background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,.1);">
                    <strong>Tổng số chunks</strong><br>
                    <span style="color: #6c5ce7; font-size: 1.2em;">${simulatedTotalChunksGenerated}</span>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,.1);">
                    <strong>Vector Database</strong><br>
                    <span style="color: #00b894; font-size: 1.2em;">✅ Saved</span>
                </div>
            `;
        }

        resultsHtml += `
                <div style="background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,.1);">
                    <strong>Tổng thời gian xử lý</strong><br>
                    <span style="color: #fd7e14; font-size: 1.2em;">${totalTimeSeconds} giây</span>
                </div>
            </div> `;

        // Error details if any
        if (simulatedFailedDownloadFiles.length > 0) {
            resultsHtml += `
                <h5 class="mt-4 text-danger">Chi tiết lỗi tải file:</h5>
                <ul class="list-unstyled text-danger small">
            `;
            simulatedFailedDownloadFiles.forEach(file => {
                resultsHtml += `<li><strong>${file.fileName}:</strong> ${file.error}</li>`;
            });
            resultsHtml += `</ul>`;
        }

        // ENHANCED: MongoDB Status Section với chunk insert details
        const mongoInfo = window.mongodbInfo || mongodbInfo;
        if (mongoInfo) {
            const mongoStatus = mongoInfo.success ? '✅ Success' : '❌ Failed';
            const statusColor = mongoInfo.success ? '#00b894' : '#e74c3c';
            const bgColor = mongoInfo.success ? '#d4edda' : '#f8d7da';
            const textColor = mongoInfo.success ? '#155724' : '#721c24';
            
            resultsHtml += `
                <div style="margin-top: 20px; padding: 15px; border-radius: 8px; background: ${bgColor}; border-left: 4px solid ${statusColor};">
                    <h5 style="color: ${statusColor}; margin-bottom: 10px;">
                        <i class="fas fa-database"></i> MongoDB Status: ${mongoStatus}
                    </h5>
            `;
            
            if (mongoInfo.success) {
                // Success case - show chunk insert details
                resultsHtml += `
                    <div style="color: ${textColor}; font-size: 0.9em;">
                        <div style="margin-bottom: 8px;">
                            <strong>Database:</strong> 
                            <code style="background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 3px;">${mongoInfo.database || 'edu_agent_db'}</code>
                        </div>
                        <div style="margin-bottom: 8px;">
                            <strong>Collection:</strong> 
                            <code style="background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 3px;">${mongoInfo.collection || 'lectures'}</code>
                        </div>
                `;
                
                // THÊM: Hiển thị thông tin chunk inserts
                if (mongoInfo.inserted_count !== undefined) {
                    resultsHtml += `
                        <div style="margin-bottom: 8px;">
                            <strong>Chunks Inserted:</strong> 
                            <span style="color: #00b894; font-weight: bold;">${mongoInfo.inserted_count}</span>
                            ${mongoInfo.total_chunks ? ` / ${mongoInfo.total_chunks}` : ''}
                        </div>
                    `;
                    
                    if (mongoInfo.failed_count && mongoInfo.failed_count > 0) {
                        resultsHtml += `
                            <div style="margin-bottom: 8px;">
                                <strong>Failed Inserts:</strong> 
                                <span style="color: #e74c3c; font-weight: bold;">${mongoInfo.failed_count}</span>
                            </div>
                        `;
                    }
                }
                
                if (mongoInfo.document_id && mongoInfo.document_id !== 'unknown') {
                    resultsHtml += `
                        <div style="margin-bottom: 8px;">
                            <strong>Sample Document ID:</strong> 
                            <code style="background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 3px; font-size: 0.8em;">${mongoInfo.document_id}</code>
                        </div>
                    `;
                }
                
                resultsHtml += `
                        <div style="margin-bottom: 8px;">
                            <strong>Status:</strong> 
                            <span style="color: #00b894; font-weight: bold;">✅ Individual chunks saved successfully</span>
                        </div>
                    </div>
                `;
                
            } else {
                // Error case - show error details
                resultsHtml += `
                    <div style="color: ${textColor}; font-size: 0.9em;">
                        <div style="margin-bottom: 8px;">
                            <strong>Error:</strong> Failed to save chunks to MongoDB
                        </div>
                `;
                
                if (mongoInfo.error) {
                    resultsHtml += `
                        <div style="margin-bottom: 8px;">
                            <strong>Details:</strong> 
                            <code style="background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 3px; font-size: 0.8em;">${mongoInfo.error}</code>
                        </div>
                    `;
                }
                
                resultsHtml += `
                        <div style="margin-bottom: 8px;">
                            <strong>Suggestion:</strong> Check MongoDB connection and credentials
                        </div>
                    </div>
                `;
            }
            
            resultsHtml += `</div>`;
        }

        // Vector Database Info (giữ lại từ code cũ)
        if (isSuccess && window.vectorDatabaseInfo) {
            resultsHtml += `
                <div style="margin-top: 20px; padding: 15px; border-radius: 8px; background: #e3f2fd; border-left: 4px solid #2196f3;">
                    <h5 style="color: #1976d2; margin-bottom: 10px;">
                        <i class="fas fa-database"></i> Vector Database Info:
                    </h5>
                    <div style="color: #0d47a1; font-size: 0.9em;">
                        <div style="margin-bottom: 8px;">
                            <strong>Type:</strong> ${window.vectorDatabaseInfo.type}
                        </div>
                        <div style="margin-bottom: 8px;">
                            <strong>Location:</strong> ${window.vectorDatabaseInfo.location}
                        </div>
                    </div>
                </div>
            `;
        }

        finalResultsContent.innerHTML = resultsHtml;
    }
    // Đảm bảo khung chọn dữ liệu và nút "Bắt đầu xử lý" vẫn hiển thị
    if (processingSection) processingSection.style.display = 'block';
}
// THÊM: Reset MongoDB info trong resetUpload
function resetUpload() {
    selectedFiles = [];
    minioFilesToProcess = [];
    folderFiles = [];
    folderMetadataList = [];
    currentFolderFileIndex = 0;
    isProcessingFolder = false;
    
    // Cleanup pipeline resources
    cleanupPipelineResources();
    
    if (fileInput) fileInput.value = "";
    if (folderInput) folderInput.value = "";
    selectedDataSource = null;
    currentFileMetadata = null;

    // ENHANCED: Reset MongoDB và Vector Database info
    window.mongodbInfo = null;
    window.vectorDatabaseInfo = null;
    mongodbInfo = null;

    const uploadOption = document.getElementById('uploadOption');
    if (uploadOption) {
        uploadOption.style.display = 'block';
    }
    if (metadataPreviewBox) metadataPreviewBox.style.display = 'none';
    if (saveToMinioBtn) saveToMinioBtn.style.display = 'none';
    if (startProcessingBtn) {
        startProcessingBtn.style.display = 'none';
        startProcessingBtn.classList.remove('btn-primary');
        startProcessingBtn.classList.add('btn-secondary');
        startProcessingBtn.disabled = true;
    }
    if (saveAllToMinioBtn) saveAllToMinioBtn.style.display = 'none';
    if (sourceStatus) sourceStatus.style.display = 'none';
    if (folderInfoBox) folderInfoBox.style.display = 'none';
    if (folderNavigationButtons) folderNavigationButtons.style.display = 'none';
    
    resetProgressSteps();
    if (finalResults) finalResults.style.display = 'none';

    if (minioFolderSelect) {
        $(minioFolderSelect).val(null).trigger('change');
    }

    // Reset simulated results
    simulatedTotalFilesProcessed = 0;
    simulatedSuccessfullyDownloadedFiles = 0;
    simulatedFailedDownloadFiles = [];
    simulatedTotalChunksGenerated = 0;
    simulatedTotalProcessingTimeMs = 0;
    simulatedProcessStartTime = null;

    if (processingSection) processingSection.style.display = 'none';
    showInitialForms();
}