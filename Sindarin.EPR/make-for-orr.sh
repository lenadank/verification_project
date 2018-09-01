#!/bin/zsh

mkdir -p ~/Downloads/orr

export PATH=/opt/local/bin:$PATH

for file in "$@"
  do echo $file
  python src/analyze.py $file && cp $TMPDIR/synopsis.smt2 ~/Downloads/orr/$(basename $file).smt2
done

