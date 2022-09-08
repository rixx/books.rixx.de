#!/bin/zsh

for index_path in **/**/index.md; do
    book_path="$(dirname "$index_path")"
    plot_path="$book_path"/plot.md
    if [[ ! -a "$plot_path" ]]; then
        if ! grep -q "$book_path" skip-plot; then
            break
        fi
    fi
done

vim -O "$plot_path" "$index_path"
