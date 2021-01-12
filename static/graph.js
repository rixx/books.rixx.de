// Load data
d3.json("/graph.json").then(data => {
    // footerHeight = 54
    // headerHeight = 46
    const height = window.innerHeight - 54 - 46;
    const width = window.innerWidth
    const container = document.querySelector("#book-graph")
    container.style.height = height
    container.style.width = width

    // Let's list the force we wanna apply on the network
    const simulation = d3.forceSimulation(data.nodes)
          .force("link", d3.forceLink(data.links).id(d => d.id))
          .force("charge", d3.forceManyBody().strength(-20))
          // .force("center", d3.forceCenter(width / 2, height / 2)); // this would be for a connected graph
          .force("x", d3.forceX())
          .force("y", d3.forceY());

    const svg = d3.select("#book-graph").append("svg")
        .attr("viewBox", [-width / 2, -height / 2, width, height]);

    //const color = {
      //const scale = d3.scaleOrdinal(d3.schemeCategory10);
      //return d => scale(d.id);
    //}

    drag = simulation => {
      function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }
      function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }
      
      function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }
      return d3.drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended);
    }

    const link = svg.append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(data.links)
        .join("line");
        //.attr("stroke-width", d => Math.sqrt(d.value));

    const node = svg.append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .selectAll("circle")
        .data(data.nodes)
        .join("circle")
        .attr("r", 5)
        //.attr("fill", color)
        .attr("fill", "red")
        .on("click", (d, i) => {window.location.href = "/" + i.id})
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
