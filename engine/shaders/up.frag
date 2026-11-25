#version 330 core
uniform sampler2D u_tex; uniform vec2 u_texel; uniform float u_gain;
in vec2 uv; out vec4 frag;
void main(){
    vec3 s = vec3(0.);
    s += texture(u_tex, uv+u_texel*vec2(-2,0)).rgb + texture(u_tex, uv+u_texel*vec2(2,0)).rgb;
    s += texture(u_tex, uv+u_texel*vec2(0,-2)).rgb + texture(u_tex, uv+u_texel*vec2(0,2)).rgb;
    s += 2.*(texture(u_tex, uv+u_texel*vec2(-1,1)).rgb + texture(u_tex, uv+u_texel*vec2(1,1)).rgb
           + texture(u_tex, uv+u_texel*vec2(-1,-1)).rgb + texture(u_tex, uv+u_texel*vec2(1,-1)).rgb);
    frag = vec4(s/12.*u_gain,1.);
}