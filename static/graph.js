let isDragging = false
let currentBook = null

let node = null
let link = null
let linkMap = {}

window.addEventListener("mouseup", e => isDragging = false)

const changeSidebarBook = (book) => {
    // create HTML
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
    div.innerHTML = content

    const wrapper = document.querySelector("#graph-sidebar")
    wrapper.replaceChild(div, wrapper.querySelector("#book-preview"))
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

d3.json("/graph.json").then(data => {

    data.links.forEach(link => {
        linkMap[`${link.source},${link.target}`] = true
    })

    const container = document.querySelector("#book-graph")
    const height = container.clientHeight;
    const width = container.clientWidth;

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

    const svg = d3.select("#book-graph").append("svg")
        .attr("viewBox", [-width / 2, -height / 2, width, height]);  // For unconnected graph
        //.attr("viewBox", [0, 0, width, height]);  // For connected graph

    link = svg.append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(data.links)
        .join("line");
        //.attr("stroke-width", d => Math.sqrt(d.value));

    const colorScale = d3.scaleLinear().domain([0, 20]).range(["grey", "blue"]);
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
        // .attr("fill", (d) => d.color || "grey")
        .attr("class", "bunt")
        .attr("style", d => `--book-color: ${d.color || "grey"}`)
        .on("mouseenter", hoverHandler)
        .on("mouseleave", mouseLeaveHandler)
        .call(drag(simulation));

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
    document.querySelector("input#graph-search").value = decodeURI(window.location.hash.substr(1))
    changeSearch()
})

document.addEventListener('DOMContentLoaded', function() {
    document.querySelector("input#graph-search").addEventListener("input", changeSearch)
}, false);
