#!/bin/sh
# D7 のうち大きいファイルを /tmp に作る（リポジトリには置かない）。
# サイズ検査は中身を読まずに弾くので、ダミーのバイト列でよい。
# 使い方: sh backend/tests/fixtures/make_large.sh
set -eu
DIR="${1:-/tmp/r2b-fixtures-large}"
mkdir -p "$DIR"

# 1ファイル 20MB の上限を超えるファイル（FILE_TOO_LARGE）
dd if=/dev/zero of="$DIR/oversize_21mb.pdf" bs=1048576 count=21 2>/dev/null

# 合計 50MB の上限を超える組み合わせ（TOTAL_SIZE_EXCEEDED）
# 19MB × 3 = 57MB。1ファイルは上限内なので、合計側だけで弾かれることを確かめられる。
for i in 1 2 3; do
  dd if=/dev/zero of="$DIR/total_over_${i}_19mb.pdf" bs=1048576 count=19 2>/dev/null
done

echo "作成しました: $DIR"
ls -lh "$DIR"
