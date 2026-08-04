[out:xml][timeout:180];
way["highway"~"trunk|primary|trunk_link|primary_link"]["ref"~"NH.?16|NH.?5"](17.60,83.10,18.40,84.00) -> .nh16;
way(around.nh16:400)["highway"~"trunk|primary|secondary|tertiary|trunk_link|primary_link|secondary_link|tertiary_link"] -> .nearby;
(.nh16; .nearby;);
(._;>;);
out body;
