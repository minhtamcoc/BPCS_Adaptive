# Adaptive BPCS + Conjugation

## Muc dich

Bai thuc hanh giup sinh vien hieu va thuc hien adaptive BPCS, dynamic
threshold va checkerboard conjugation trong bai toan giau tin video.

Sinh vien se tinh alpha cua block du lieu, thuc hien conjugation khi
block chua du phuc tap, sau do tinh nguong cuoi de chon vung nhieu phu
hop tren frame video.

## File ban dau

```text
video.mp4
adaptive_encode.py
adaptive_decode.py
```

## Task 1: Tach video va tinh nguong adaptive

Xem thong tin video:

```bash
ffmpeg -hide_banner -i video.mp4 2> video_info.txt
cat video_info.txt
```

Tach frame va audio:

```bash
mkdir frames
ffmpeg -i video.mp4 frames/frame_%04d.png
ffmpeg -hide_banner -i video.mp4 -q:a 0 -map a audio.mp3
```

Chay phan tich adaptive:

```bash
python3 adaptive_encode.py --analyze
```

Ket qua can co:

```text
threshold_report.txt
message_blocks.json
```

Can doc cac gia tri:

```text
min_alpha_prime
max_alpha_prime
final_threshold
```

## Task 2: Kiem tra conjugation

Mo file message_blocks.json:

```bash
cat message_blocks.json
```

Moi block du lieu co:

```text
alpha_before
alpha_after
conjugated
```

Neu alpha_before nho hon BASE_ALPHA, block du lieu duoc conjugate:

```text
S* = S xor Wc
```

Trong do Wc la checkerboard pattern.

## Task 3: Nhung bang Adaptive BPCS

Mo file encode:

```bash
nano adaptive_encode.py
```

Chu y cac bien:

```text
BASE_ALPHA
ADAPTIVE_MARGIN
MAX_FINAL_THRESHOLD
TARGET_FRAME_INDEX
SECRET_DATA
BIT_PLANE
CHANNEL
```

Chay nhung:

```bash
python3 adaptive_encode.py --embed
```

Ket qua can co:

```text
adaptive_position.json
adaptive_output.avi
```

## Task 4: Tach frame tu video da giau tin

```bash
mkdir adaptive_extract_frames
ffmpeg -hide_banner -i adaptive_output.avi adaptive_extract_frames/frame_%04d.png
```

## Task 5: Tach tin

Mo file decode:

```bash
nano adaptive_decode.py
```

Trong file mau, TARGET_FRAME_INDEX duoc dat la 101 vi video stego
thuong bi lech 1 frame sau khi xuat lai bang ffmpeg. Neu thu nghiem voi
video khac, sinh vien co the so sanh so frame va dieu chinh lai gia tri
nay.

Chay:

```bash
python3 adaptive_decode.py
```

Ket qua can co:

```text
recovered_adaptive_secret.txt
```

## Checkwork

Tu terminal Labtainer ben ngoai container:

```bash
checkwork
```

Lab co 5 muc cham:

```text
cw1: co threshold_report.txt voi final_threshold
cw2: co message_blocks.json voi thong tin conjugation
cw3: co adaptive_position.json sau khi embed
cw4: da tach frame vao adaptive_extract_frames
cw5: recovered_adaptive_secret.txt dung thong diep
```

## Stoplab

```bash
stoplab bpcs_adaptive
```
