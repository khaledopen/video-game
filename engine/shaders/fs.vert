#version 330 core
in vec2 in_pos; out vec2 uv;
void main(){ uv = in_pos*.5+.5; gl_Position = vec4(in_pos,0.,1.); }