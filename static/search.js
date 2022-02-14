let bookData = null
let bookDataLoading = false


const renderSearchResults = (books, tags) => {
    // build HTML
    const wrapper = document.querySelector("#search-container")
    const div = document.createElement("div")
    div.id = "search-results"
    if (!books.length && !tags.length) {
        div.classList.add("empty")  // allows us to always replace, because we're lazy like that
    } else {
        let content = ""
        books.forEach(book => {
            content += `<a href="/${book.id}/" class="result book-result">`
            if (book.cover) {
                content += `<img class="cover" src="/${book.id}/thumbnail.jpg">`
            } else {
                content += `<img class="cover" src="/static/cover.png">`
            }
            let title = book.name
            if (book.series) title += ` (${book.series})`
            let rating = ""
            if (book.rating) {
                rating = "★".repeat(book.rating) + "☆".repeat(5 - book.rating)
                rating = `<div class="rating">${rating}</div>`
            }
            content += `<div class="search-content"><div class="book-title">${title}</div><div class="book-author">${book.author}</div>${rating}</div></a>`
        })
        if (tags.length) content += "<hr>"
        tags.forEach(tag => {
            content += `<a href="/lists/${tag.slug}/" class="result tag-result"><div class="tag-name">Book list: ${tag.name}</div></a><hr>`
        })
        div.innerHTML = content
    }
    wrapper.replaceChild(div, wrapper.querySelector("#search-results"))
}

const updateSearch = () => {
    const searchInput = document.querySelector("input#search")
    const search = searchInput.value

    const searchTerms = search
        .split(" ")
        .filter(d => d.length)
        .map(d => d.toLowerCase().trim())

    if (!searchTerms.length) return renderSearchResults([], [])

    const bookHits = bookData.books.filter(book => book.search.filter(d => searchTerms.some(term => d.includes(term))).length)
    const tagHits = bookData.tags.filter(tag => tag.search.filter(d => searchTerms.some(term => d.includes(term))).length)
    renderSearchResults(bookHits, tagHits)
}

const loadBookData = () => {
    if (bookData) {
        return Promise.resolve()
    }
    bookDataLoading = true  // todo render

    return fetch("/search.json").then(response => response.json().then(data => {
        bookData = data
        bookDataLoading = false  // todo undo render
        const searchInput = document.querySelector("input#search")
        searchInput.removeEventListener("focus", loadBookData)
        searchInput.addEventListener("input", updateSearch)
        console.log("Book data loaded.")
        updateSearch()
    }))
}

const init = () => {
    const searchInput = document.querySelector("input#search")
    searchInput.addEventListener("focus", loadBookData)
}

if (document.readyState !== "loading") { init() } else {
    document.addEventListener('DOMContentLoaded', prepareSearch, false)
}
