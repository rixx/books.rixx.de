const randomBook = () => {
    loadBookData().then(() => {
        const index = Math.floor(Math.random() * bookData.books.length)
        const book = bookData.books[index]
        // render starts here, refactor ig
        console.log(book)
        let content = ""
        content += `<div class="book-card"><a href="/${book.id}/" class=""><div class="book-metadata"><div class="book-thumbnail"><div class="cover-wrapper">`
        if (book.cover) {
            content += `<img class="cover" src="/${book.id}/thumbnail.jpg">`
        } else {
            content += `<img class="cover" src="/static/cover.png">`
        }
        content += "</div></div>"
        let title = book.name
        if (book.series) title += ` (${book.series})`
        content += `<p class="title">${title}</p><small>by ${book.author}</small>`
        let rating = ""
        if (book.rating) {
            rating = "★".repeat(book.rating) + "☆".repeat(5 - book.rating)
            rating = `<div class="rating">${rating}</div>`
        }
        content += `<div class="rating">${rating}</div>`
        content += "</div></a></div>"
        document.querySelector("#random-result").innerHTML = content
    })
}

const initRandom = () => {
    const randomButton = document.querySelector("button#random")
    randomButton.addEventListener("click", randomBook)
}

if (document.readyState !== "loading") { initRandom() } else {
    document.addEventListener('DOMContentLoaded', prepareSearch, false)
}
