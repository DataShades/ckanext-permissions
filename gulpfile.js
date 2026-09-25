const { resolve } = require("path");
const { src, watch, dest } = require("gulp");
const if_ = require("gulp-if");
const sass = require("gulp-sass")(require("sass"));
const sourcemaps = require("gulp-sourcemaps");
const cleanCSS = require("gulp-clean-css");
const header = require("gulp-header");
const touch = require("gulp-touch-fd");

const with_sourcemaps = () => !!process.env.DEBUG;

const themeDir = resolve("ckanext/permissions_manager/theme");
const assetsDir = resolve("ckanext/permissions_manager/assets");

const banner = "/* Built automatically from theme/*.scss — do not edit. */\n";

const build = () => {
    const debug = !!process.env.DEBUG;

    return src(resolve(themeDir, "style.scss"))
        .pipe(if_(with_sourcemaps(), sourcemaps.init()))
        .pipe(
            sass({ outputStyle: debug ? "expanded" : "compressed" }).on("error", sass.logError)
        )
        .pipe(if_(!debug, cleanCSS({ level: 2 })))
        .pipe(if_(!debug, header(banner)))
        .pipe(if_(with_sourcemaps(), sourcemaps.write()))
        .pipe(dest(resolve(assetsDir, "css")))
        .pipe(touch());
};

const watchSource = () => {
    watch(themeDir + "/**/*.scss", { ignoreInitial: false }, build);
};

exports.build = build;
exports.watch = watchSource;
