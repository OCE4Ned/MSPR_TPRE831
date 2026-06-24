import { type RouteConfig, index, layout, route } from "@react-router/dev/routes";

export default [
  layout("layouts/dashboard.tsx", [
    index("routes/group.tsx"),
    route("site", "routes/site.tsx"),
  ]),
] satisfies RouteConfig;
