// Pluie, poussiere et lignes de vitesse : entierement sur le GPU
uniform int u_mode; uniform float u_amount;
in vec2 in_pos; in vec4 i_seed;
out vec2 v_uv; out float v_a; out vec3 v_c;
void main(){
    v_uv = in_pos;
    float t = u_cam.w; vec3 c, ax; float len, wid;
    if(u_mode==0){                                   // pluie
        vec3 box = vec3(26., 13., 42.);
        vec3 vel = vec3(1.2, -15., 0.);
        c = fract(i_seed.xyz + vel*t/box - vec3(0.,0.,u_track.x/box.z*.85)) * box;
        c += vec3(u_cam.x - box.x*.5, u_cam.y - 5.5, u_cam.z - 2.);
        ax = normalize(vec3(1.2,-15.,-u_track.y*.28)); len = .34 + .010*u_track.y; wid = .0085;
        v_c = vec3(.55,.65,.85); v_a = .34*step(i_seed.w, u_amount);
    } else if(u_mode==1){                            // poussiere / flocons lumineux
        vec3 box = vec3(40., 9., 60.);
        c = fract(i_seed.xyz + vec3(.036*sin(t*.4+i_seed.w*30.), .004*sin(t+i_seed.x*20.), 0.) - vec3(0.,0.,u_track.x/box.z)) * box;
        c += vec3(u_cam.x - 20., .1, u_cam.z - 2.);
        ax = normalize(vec3(.3,.0,-1.)); len = .02 + u_track.y*.006; wid = .028;
        v_c = ENV==1 ? vec3(1.2,.62,.30) : vec3(.9,.95,1.1); v_a = .40*step(i_seed.w, u_amount);
    } else {                                         // lignes de vitesse
        float a = i_seed.x*2.*PI, r = 3.6 + 6.5*i_seed.y;
        float L = 80.;
        float z = fract(i_seed.z - u_track.x/L*1.3 - t*.2) * L;
        c = vec3(u_cam.x + cos(a)*r*1.5, u_cam.y + abs(sin(a))*r - .6, z - 4.);
        ax = vec3(0.,0.,1.); len = 5. + 7.*i_seed.w; wid = .016 + .012*i_seed.w;
        v_c = mix(vec3(.65,.85,1.), u_acc.rgb*1.6, step(.55,i_seed.w));
        v_a = u_amount*.55*smoothstep(0.,14.,z)*smoothstep(80.,50.,z);
    }
    if(u_mode<2) v_a *= smoothstep(3.,7.5,length(c-u_cam.xyz));
    vec3 tv = normalize(u_cam.xyz - c); vec3 sd = normalize(cross(ax,tv));
    vec3 p = c + ax*in_pos.y*len + sd*in_pos.x*wid;
    gl_Position = u_vp * vec4(p,1.);
}