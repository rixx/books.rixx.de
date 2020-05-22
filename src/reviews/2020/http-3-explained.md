---
book:
  author: Daniel Stenberg
  cover_image: http-3-explained.jpg
  cover_image_url: https://i.gr-assets.com/images/S/compressed.photo.goodreads.com/books/1547455205l/43560466._SX98_.jpg
  goodreads: '43560466'
  publication_year: null
  slug: http-3-explained
  title: HTTP/3 explained
plan:
  date_added: '2020-01-11'
review:
  date_read: 2020-01-12
  date_started: null
  did_not_finish: false
  rating: 4
---

HTTP/3 explained is a little booklet by curl developer Daniel Stenberg explaining the principles and history behind HTTP/3. I liked the inclusion of recent history and explanation of discussions in the working groups. There is also some frank discussion of potential downsides in terms of security, performance, and adaptability, but usually there is one argument presented per point, so I had the impression that my opinion was being nudged (because of the lack of differing arguments). This is mostly due to the booklets short texts that don't expand much upon anything. Both the writing and the general structure are a bit rough around the edges.<br /><br />This book is definitely worth the read to get a general impression of the structure of HTTP/3, where it operates, and what its governing principles are. I now have a feeling for its complexity, but I can't say that "reimplement TCP realm logic on UDP" has completely inspired my trust. Some of the performance shortcuts seem like vulns/side channels waiting to be exploited. We'll get real life data soon-ish though, since the nginx implementation is work in progress already, and clients are also under way and/or implemented.<br /><br />I read up a bit on the meeting minutes, and some of the most debated topics have been skipped, such as the functioning of load balancers (surely interesting for most users). Functionally, a load balancer is one of those tampering middleboxes the protocol means to include, only that it's *trusted*. I wish this had been mentioned in the book.
