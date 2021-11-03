let isDragging = false
let isHovering = false
let currentBook = null

let node = null
let link = null
let graph = createGraph()
let path = null

let startNode = null
let endNode = null
let currentPath = null
let currentPathLinks = null
let currentHash = {}

window.addEventListener("mouseup", e => isDragging = false)


const updateHash = (obj) => {
    Object.entries(obj).forEach(data => {
        if (data && data.length > 1) {
            currentHash[data[0]] = data[1]
        }
    })
    window.location.hash = Object.entries(currentHash).filter(value => value[1]).map(value => `${value[0]}=${encodeURI(value[1])}`).join("&")
}

const deletePath = () => {
    currentPath = null
    currentPathLinks = null
    changeGraphHighlight()
    document.querySelector("#book-route h3").innerHTML = "Finding route …"
}

const updatePath = () => {
    if (startNode && endNode) {
        currentPath = path.find(startNode.id, endNode.id)
        currentPathLinks = []
        link.each(l => {
            for (let i=0; i < currentPath.length - 1; i++) {
                const source = currentPath[i]
                const target = currentPath[i + 1]
                if ((l.target && l.source) && ((l.target.id === target.id && l.source.id === source.id) || (l.target.id === source.id && l.source.id === target.id))) {
                    currentPathLinks.push(l)
                }
            }

        })
        changeGraphHighlight()
        document.querySelector("#book-route h3").innerHTML = `Route found: ${currentPathLinks.length} hops`
    } else {
        document.querySelector("#book-route h3").innerHTML = "Finding route …"
    }
}


const setStart = (book) => {
    if (!book) {
        startNode = null
        document.querySelector("#start-name").innerHTML = ""
        document.querySelector("#start-delete").style.display = "none"
        deletePath()
        updateHash({start: null})
        if (endNode) {
            document.querySelector("#book-route").style.display = "block"
        } else {
            document.querySelector("#book-route").style.display = "none"
        }
    } else {
        startNode = book
        document.querySelector("#start-name").innerHTML = `${book.name} by ${book.author}`
        document.querySelector("#start-delete").style.display = "inline-block"
        document.querySelector("#book-route").style.display = "block"
        updatePath()
        updateHash({start: book.id})
    }
}

const setEnd = (book) => {
    if (!book) {
        endNode = null
        document.querySelector("#end-name").innerHTML = ""
        document.querySelector("#end-delete").style.display = "none"
        deletePath()
        updateHash({end: null})
        if (startNode) {
            document.querySelector("#book-route").style.display = "block"
        } else {
            document.querySelector("#book-route").style.display = "none"
        }
    } else {
        endNode = book
        document.querySelector("#end-name").innerHTML = `${book.name} by ${book.author}`
        document.querySelector("#end-delete").style.display = "inline-block"
        updatePath()
        updateHash({end: book.id})
        document.querySelector("#book-route").style.display = "block"
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
        content += `${link}<img class="cover" src="/${book.id}/thumbnail.jpg"></a>`
    } else {
        content += `${link}<img class="cover" src="/static/cover.png"></a>`
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
    return !!(graph.getLink(a.id, b.id))
}

const changeGraphHighlight = () => {
    node.classed("bunt", (d) => {
        // This could be a single line boolean expression but it's a pain to debug
        const relevantCurrentBook = currentBook && (isDragging || isHovering)
        if (!relevantCurrentBook && !currentPath) {
            // When nothing is highlighted, everything is highlighted
            return true
        }
        if (relevantCurrentBook && (d === currentBook || (currentBook && isConnected(d, currentBook)))) {
            // If this book is active or connected to the active book
            return true
        }
        if (currentPath && currentPath.includes(d)) {
            return true
        }
        return false
    })
    if (currentPath) {
        node.classed("path-hit", d => currentPath.filter(p => p.id === d.id).length)
        link.classed("path-hit", d => currentPathLinks.filter(l => l.index == d.index).length)
    }
    if (currentBook && (isHovering || isDragging)) {
        node.classed("active", (d) => d === currentBook || isConnected(d, currentBook))
        link.classed("bunt", (d) => d.source.id === currentBook.id || d.target.id === currentBook.id)
            .attr("stroke", (d) => (d.source.id === currentBook.id || d.target.id === currentBook.id) ? currentBook.color : null)
    } else {
        node.classed("active", false)
        link.classed("bunt", false)
            .attr("stroke", null)
    }
}

const changeSearch = () => {
    const search = document.querySelector("input#graph-search").value
    updateHash({search})
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
    isHovering = true
    changeSidebarBook(i)
    changeGraphHighlight()
}
const mouseLeaveHandler = (d, i) => {
    isHovering = false
    if (isDragging) return
    changeGraphHighlight()
}

d3.json("/graph.json").then(data => {

    data.nodes.forEach(node => {
        graph.addNode(node.id, node)
    })
    data.links.forEach(link => {
        graph.addLink(link.source, link.target)
        graph.addLink(link.target, link.source)
    })
    path = ngraphPath.aStar(graph)

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

    try {
        currentHash = window.location.hash.substr(1).split('&').reduce((res, item) => {
            if (item.includes("=")) {
                var parts = item.split('=')
                res[parts[0]] = decodeURI(parts[1])
                return res
            }
            return res
        }, {});
        console.log(currentHash)

    } catch {}

    if (currentHash.search) document.querySelector("input#graph-search").value = currentHash.search
    changeSearch()
    const start = graph.getNode(currentHash.start)
    if (start) setStart(start.data)
    const end = graph.getNode(currentHash.end)
    if (end) setEnd(end.data)
})

document.addEventListener('DOMContentLoaded', function() {
    document.querySelector("input#graph-search").addEventListener("input", changeSearch)
}, false);
