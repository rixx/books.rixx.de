let isDragging = false
let currentBook = null

window.addEventListener("mouseup", e => isDragging = false)

const changeCurrentBook = (book) => {
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

d3.json("/graph.json").then(data => {
    // footerHeight = 54
    // headerHeight = 46
    const height = window.innerHeight;
    const width = window.innerWidth - 50
    const container = document.querySelector("#book-graph")
    container.style.height = height
    container.style.width = width

    // Let's list the force we wanna apply on the network
    const simulation = d3.forceSimulation(data.nodes)
          .force("link", d3.forceLink(data.links).id(d => d.id))
          .force("charge", d3.forceManyBody().strength(-40))
          // .force("center", d3.forceCenter(width / 2, height / 2)); // this would be for a connected graph
          .force("x", d3.forceX())
          .force("y", d3.forceY());

    const svg = d3.select("#book-graph").append("svg")
        .attr("viewBox", [-width / 2, -height / 2, width, height]);

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
        if (currentBook == i.id) return
        changeCurrentBook(i)
    }

    const link = svg.append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(data.links)
        .join("line");
        //.attr("stroke-width", d => Math.sqrt(d.value));

    const colorScale = d3.scaleLinear().domain([0, 20]).range(["grey", "blue"]);
    const node = svg
        .append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .selectAll("circle")
        .data(data.nodes)
        .join("a")
        .attr("href", (d) => "/" + d.id)
        .append("circle")
        .attr("r", (d) => 5 + (d.rating || 0))
        //.attr("fill", (d) => colorScale(d.connections))
        .attr("fill", (d) => d.color || "grey")
        .on("mouseover", hoverHandler)
        .call(drag(simulation));


    node.append("title")
        .text(d => d.name);

    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);
    });
})
