# Với n = 0 ta có S(n) = 0. Đây là phần cơ sở cho điều kiện dừng của lời gọi đệ quy của hàm S(n).

**Source:** https://loigiaihay.com/bai-2-thiet-ke-thuat-toan-de-quy-chuyen-de-tin-hoc-11-ket-noi-tri-thuc-a186131.html
**Extracted:** 2025-07-19 02:00:44
**Content Length:** 5405 characters

---

Với n = 0 ta có S(n) = 0. Đây là phần cơ sở cho điều kiện dừng của lời gọi đệ quy của hàm S(n).

Bước 3. Dễ thấy S(n) = n + S(n - 1) là công thức truy hồi của hàm S(n) và là cơ sở của lời gọi đệ quy của hàm. Chương trình như sau:

Trao đổi, thảo luận và tìm hiểu ý tưởng thực hiện các tính toán sau bằng kĩ thuật đệ quy

Bước 3. Dễ thấy S(n) = n + S(n - 1) là công thức truy hồi của hàm S(n) và là cơ sở của lời gọi đệ quy của hàm.Chương trình như sau:

Bước 2. Điều kiện là n \geq 0 và theo quy ước thì exp(a,0) = 1 với mọi a. Đây chính là phần cơ sở cho điều kiện dừng của lời gọi đệ quy của hàm exp(a,n).

Bước 3. Ta có an=a*an-1suy ra exp(a,n) = a \times exp(a,n-1), đây là công thức truy hồi tính exp(a,n). Từ đó có thể thiết lập lời gọi đệ quy của hàm này.

Bước 2. Điều kiện là n \geq 0 và quy ước 0! = 1, tức là giaithua (0) = 1. Đây là cơ sở cho điều kiện dừng của lời gọi đệ quy của hàm giaithua(n).

Bước 3. Ta có công thức giaithua(n) = n \times giaithua(n-1), đây là công thức truy hồi tính giaithua(n). Từ đó dễ dàng thiết lập lời gọi đệ quy cho hàm này.

Hãy chỉ ra phần cơ sở và phần đệ quy của các chương trình trên

Phần đệ quy: S(n) = n + S(n - 1)

Vì sao trong ý tưởng thiết kế đệ quy trên, yêu cầu từ bài toán với kích thước lớn cần phải đưa về cùng bài toán đó với kích thước nhỏ hơn?

Trong ý tưởng thiết kế đệ quy, yêu cầu đưa bài toán với kích thước lớn về cùng bài toán đó với kích thước nhỏ hơn bởi vì các bài toán lớn có thể được phân chia thành các bài toán con nhỏ hơn và tương tự như vậy cho đến khi đạt được bài toán nhỏ nhất mà ta có thể giải quyết trực tiếp. Khi đó, ta sử dụng kết quả của các bài toán con này để giải quyết bài toán ban đầu lớn hơn. Nhờ vậy, lời giải ngắn gọn và dễ hiểu hơn.

Chúng ta đã biết thuật toán tìm kiếm nhị phân trên các dãy phần tử đã sắp xếp. Hãy tìm tới thiết kế mới của thuật toán này theo kĩ thuật đệ quy. Trao đổi, thảo luận và trả lời các câu hỏi sau:

1. Nêu ý tưởng chính của giải thuật tìm kiếm nhị phân sử dụng đệ quy

2. Vị trí nào trong thuật toán có thể gợi ý cho kĩ thuật đệ quy?

3. Phần cơ sở của thiết kế đệ quy nằm ở bước nào?

1. Ý tưởng chính của giải thuật tìm kiếm nhị phân sử dụng đệ quy là phân chia dãy phần tử đã sắp xếp thành hai nửa bằng nhau, tìm kiếm phần tử cần tìm trong nửa phù hợp và tiếp tục phân chia và tìm kiếm đệ quy cho đến khi tìm thấy phần tử hoặc không tìm thấy. 2. Vị trí trong thuật toán có thể gợi ý cho kĩ thuật đệ quy là phần phân chia dãy phần tử thành hai nửa bằng nhau, tìm kiếm trong nửa phù hợp và tiếp tục phân chia và tìm kiếm đệ quy cho đến khi tìm thấy phần tử hoặc không tìm thấy. Đây là một bài toán con nhỏ hơn của bài toán ban đầu và có thể được giải quyết bằng cùng một thuật toán đệ quy. 3. Phần cơ sở của thiết kế đệ quy nằm ở bước cuối cùng của thuật toán, khi không còn cách nào để phân chia dãy phần tử nữa và ta chỉ còn lại một phần tử hoặc không có phần tử nào để tìm kiếm. Khi đó, ta kết luận bài toán đệ quy đã được giải quyết và trả về kết quả.

Trong chương trình trên lệnh nào đóng vai trò là phần cơ sở của đệ quy?

Trong chương trình đệ quy, lệnh có vai trò là phần cơ sở của đệ quy là lệnh kết thúc đệ quy, hay còn gọi là điều kiện dừng. Lệnh này được sử dụng để đảm bảo rằng quá trình đệ quy sẽ dừng lại khi đạt được điều kiện mong muốn.

Trong thuật toán tìm kiếm nhị phân đệ quy, lệnh kết thúc đệ quy có thể là điều kiện tìm thấy phần tử cần tìm trong dãy hoặc không còn phần tử nào để tìm kiếm. Khi đạt được điều kiện này, thuật toán sẽ không tiếp tục đệ quy và trả về kết quả.

Giả sử A = [1, 3, 7, 9] và K = 10. Nếu áp dụng chương trình trên thì cần mấy lần gọi hàm đệ quy?

Nếu áp dụng chương trình trên thì cần 4 lần gọi hàm đệ quy

Viết chương trình theo kĩ thuật đệ quy để tính hàm SL(n) là tổng các số tự nhiên lẻ nhỏ hơn hoặc bằng n

Để tính hàm SL(n) là tổng các số tự nhiên lẻ nhỏ hơn hoặc bằng n theo kĩ thuật đệ quy, ta có thể sử dụng thuật toán sau:

Cho trước dãy A. Viết chương trình đệ quy để in dãy A theo thứ tự ngược lại

Để in dãy A theo thứ tự ngược lại sử dụng kĩ thuật đệ quy, ta có thể thực hiện theo thuật toán sau:

3. Gọi đệ quy hàm in dãy A trừ phần tử cuối cùng (A[:-1]).

Để tính tổng của một dãy số A sử dụng kĩ thuật đệ quy, ta có thể thực hiện theo thuật toán sau:

Chúng ta đã biết thuật toán sắp xếp chèn trên dãy A cho trước theo hàm sau

Hãy thiết kế lại chương trình trên sử dụng kĩ thuật đệ quy

Để sắp xếp một mảng bằng thuật toán sắp xếp chèn đệ quy, ta có thể thực hiện theo thuật toán sau:

2. Trường hợp ngược lại, sắp xếp mảng con trừ phần tử cuối cùng (arr[:-1]) bằng thuật toán sắp xếp chèn đệ quy.

Bạn An đã nghĩ ra thuật toán tìm kiếm nhị phân bằng đệ quy theo cách khác như sau:

b) Phần cơ sở của đoạn lệnh trên là việc kiểm tra điều kiện kết thúc đệ quy, nếu left==right và A[left] == K thì trả về giá trị left, ngược lai nếu A[left] !=K thì trả về -1. Nếu không, tiếp tục tìm kiếm bằng cách tính giá trị mid ở giữa low và high, kiểm tra nó có bằng x hay không, nếu có thì trả về mid, nếu không thì tiếp tục tìm kiếm trong phần bên trái nếu x nhỏ hơn giá trị ở vị trí mid, hoặc phía bên phải nếu x lớn hơn giá trị ở vị trí mid. Quá trình đệ quy này sẽ tiếp tục cho đến khi tìm thấy giá trị x hoặc không tìm thấy và trả về -1.

Áp dụng kĩ thuật giải đệ quy để giải các bài toán, theo em cần phải đặc biệt lưu ý đến điều gì?

Hãy phân tích một số ưu nhược điểm của việc áp dụng kĩ thuật đệ quy trong lập trình