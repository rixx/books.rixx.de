let isDragging = false
let currentBook = null

let node = null
let link = null
let linkMap = {}

let startNode = null
let endNode = null
let currentPath = null

window.addEventListener("mouseup", e => isDragging = false)


const redrawPath = () => {
}


const deletePath = () => {
    currentPath = []
    redrawPath()
}

const updatePath = () => {
    redrawPath()
}


const setStart = (book) => {
    if (!book) {
        startNode = null
        document.querySelector("#start-name").innerHTML = ""
        document.querySelector("#start-delete").style.display = "none"
        deletePath()
    } else {
        startNode = book
        document.querySelector("#start-name").innerHTML = `${book.name} by ${book.author}`
        document.querySelector("#start-delete").style.display = "inline-block"
        updatePath()
    }
    document.querySelector("#book-route").style.display = (!startNode && !endNode) ? "none" : "block"
}

const setEnd = (book) => {
    if (!book) {
        endNode = null
        document.querySelector("#end-name").innerHTML = ""
        document.querySelector("#end-delete").style.display = "none"
        deletePath()
    } else {
        endNode = book
        document.querySelector("#end-name").innerHTML = `${book.name} by ${book.author}`
        document.querySelector("#end-delete").style.display = "inline-block"
        updatePath()
    }
    document.querySelector("#book-route").style.display = (!startNode && !endNode) ? "none" : "block"
}

const changeSidebarBook = (book) => {
    // create HTML
    currentBook = book
    const div = document.createElement("div")
    div.id = "book-preview"
    div.classList.add("book-cover")
    let content = ""
    const link = `<a href="/${book.id}/">`
    if (book.cover) {
        content += `${link}<img class="cover" src="/${book.id}/${book.cover}"></a>`
    } else {
        content += `${link}<div class="cover cover-placeholder"></div></a>`
    }
    content += `
        ${link}<div class="book-title">${book.name}</div></a>
        <div class="book-author">${book.author}</div>`
    if (book.rating) {
        const rating = "★".repeat(book.rating) + "☆".repeat(5 - book.rating)
        content += `<div class="rating">${rating}</div>`
    }
    content += `
        <div>
            <button style="display: inline-block" id="set-current-as-start">Set start</button>
            <button style="display: inline-block" id="set-current-as-end">Set end</button>
        </div>`
    div.innerHTML = content

    const wrapper = document.querySelector("#graph-sidebar")
    wrapper.replaceChild(div, wrapper.querySelector("#book-preview"))
    document.querySelector("#set-current-as-start").addEventListener("click", () => setStart(currentBook))
    document.querySelector("#set-current-as-end").addEventListener("click", () => setEnd(currentBook))
}

const isConnected = (a, b) => {
    return a.id === b.id || linkMap[`${a.id},${b.id}`] || linkMap[`${b.id},${a.id}`]
}

const changeGraphHighlight = (book) => {
    node.classed("bunt", (d) => isConnected(d, book))
    node.classed("active", (d) => isConnected(d, book))
    link.classed("bunt", (d) => d.source.id === book.id || d.target.id === book.id)
        .attr("stroke", (d) => (d.source.id === book.id || d.target.id === book.id) ? book.color : "#999")
}

const removeGraphHighlight = (book) => {
    node.classed("bunt", true)
        .classed("active", false)
    link.classed("bunt", false)
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
}

const changeSearch = () => {
    const search = document.querySelector("input#graph-search").value
    window.location.hash = encodeURI(search)
    const searchTerms = search
        .split(" ")
        .filter(d => d.length)
        .map(d => d.toLowerCase().trim())
    if (!searchTerms.length) {
        node.classed("search-hit", false)
        node.classed("search-fail", false)
        return
    }
    const searchHit = (book) => {
        for (term of searchTerms) {
            if (!(book.search.filter(d => d.includes(term)).length)) return false
        }
        return true
    }
    node.classed("search-hit", d => searchHit(d))
    node.classed("search-fail", d => !searchHit(d))
}
const hoverHandler = (d, i) => {
    if (isDragging) return
    if (currentBook === i.id) return
    changeSidebarBook(i)
    changeGraphHighlight(i)
}
const mouseLeaveHandler = (d, i) => {
    if (isDragging) return
    removeGraphHighlight()
}

d3.json("/graph.json").then(data => {

    data.links.forEach(link => {
        linkMap[`${link.source},${link.target}`] = true
    })

    const container = document.querySelector("#book-graph")
    const svg = d3.select("#book-graph").append("svg")
    link = svg.append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(data.links)
        .join("line");
        //.attr("stroke-width", d => Math.sqrt(d.value));

    node = svg
        .append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .selectAll("circle")
        .data(data.nodes)
        .join("a")
        .attr("href", (d) => "/" + d.id)
        .append("circle")
        .attr("r", (d) => 5 + (d.rating || 0))
        .attr("class", "bunt")
        .attr("style", d => `--book-color: ${d.color || "grey"}`)
        .on("mouseenter", hoverHandler)
        .on("mouseleave", mouseLeaveHandler)

    const redraw = () => {
        const height = container.clientHeight;
        const width = container.clientWidth;
        svg.attr("viewBox", [-width / 2, -height / 2, width, height]);  // For unconnected graph
        //svg.attr("viewBox", [0, 0, width, height]);  // For connected graph

        let xForce = yForce = 0.1;
        if (height > width) {
            yForce = (width / height) / 10;
            
        } else {
            xForce = (height / width) / 10;
        }
        // Let's list the force we wanna apply on the network
        const simulation = d3.forceSimulation(data.nodes)
              .force("charge", d3.forceManyBody())
              //.force("charge", d3.forceManyBody().strength(-30))  // Closer to zero = smaller graph
              .force("link", d3.forceLink(data.links).id(d => d.id))
              .force("x", d3.forceX().strength(xForce))   // This is for our graph
              .force("y", d3.forceY().strength(yForce));  // This is for our graph
              //.force("charge", d3.forceManyBody().strength(-5))  // Closer to zero = smaller graph
              //.force("center", d3.forceCenter(width / 2, height / 2)); // this would be for a connected graph

        drag = simulation => {
          function dragstarted(event) {
            isDragging = true;
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
          }
          function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
          }
          
          function dragended(event) {
            isDragging = false;
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
          }
          return d3.drag()
              .on("start", dragstarted)
              .on("drag", dragged)
              .on("end", dragended);
        }


        node.call(drag(simulation));

        const maxRadius = 7
        simulation.on("tick", () => {
            //constrains the nodes to be within a box
            node
                .attr("cx", d => Math.max(-0.5*width + maxRadius, Math.min(0.5*width - maxRadius, d.x)))
                .attr("cy", d => Math.max(-0.48*height + maxRadius, Math.min(0.48*height - maxRadius, d.y)));
                //.attr("cx", d => d.x)
                //.attr("cy", d => d.y);
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

        });
    }
    redraw()
    window.addEventListener("resize", redraw);
    document.querySelector("#start-delete").addEventListener("click", () => setStart())
    document.querySelector("#end-delete").addEventListener("click", () => setEnd())

    document.querySelector("input#graph-search").value = decodeURI(window.location.hash.substr(1))

    changeSearch()
    setStart()
    setEnd()
})

document.addEventListener('DOMContentLoaded', function() {
    document.querySelector("input#graph-search").addEventListener("input", changeSearch)
}, false);
