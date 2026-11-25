in vec2 in_pos;
out vec2 v_ndc;
void main(){ v_ndc = in_pos; gl_Position = vec4(in_pos, .99999, 1.); }
