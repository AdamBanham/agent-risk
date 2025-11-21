# Behaviour Tree Implementation

After completing the implementation for the simple, defensive,
and aggressive patterns, I had a few feelings about the process.
While the implementation for the simple pattern felt "enjoyable",
the more complex routing constructs for the latter were measureably
more painful. As I only had the terminal and my code, I felt that
getting a good mental model for what was causing an infinite loop
for retries was very difficult. I feel like without a good set of tooling
around the BTs for testing and development, you are often left with testing
in the real simulation which can be time consuming.

I did reuse a fair bit of the constructs that I was working with for
most of the implementations. But, I was mostly working off the blackboard
to share information between nodes. Some nodes were setup nodes for later
compute nodes which would be somewhat complex. These nodes have a bit of
boilerplate as well to get going so it adds a bit of noise into the
codebase.

A pattern that emerged from the implementation (for better or worse),
would be to come up with initial state, create a collection, loop
through the collection until it was empty or some condition was met.
I am also not sure if I was experiencing learning pains from the framework
or just the notation.

### Video Tutorials

<https://www.youtube.com/watch?v=vqbV7mysL84>