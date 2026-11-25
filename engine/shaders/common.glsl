#version 330 core
layout(std140) uniform Frame {
    mat4 u_vp;
    vec4 u_cam;        // xyz camera, w temps
    vec4 u_track;      // s modulo 19200, vitesse m/s, portee, miroir (1 ou -1)
    vec4 u_fog;        // rgb, densite
    vec4 u_sun;        // direction, w = avancement nuit (mode Night)
    vec4 u_suncol;     // rgb, w = heure (variation de lumiere)
    vec4 u_sky;        // ambiant ciel, w = index d'environnement
    vec4 u_gnd;        // ambiant sol, w = humidit??
    vec4 u_head;       // x joueur, intensit?? phares, z avant, demi-largeur route
    vec4 u_lamp;       // rgb, puissance
    vec4 u_edge;       // rgb, espacement des lampadaires
    vec4 u_edge2;      // rgb, courbure
    vec4 u_right;      // axe camera, w = tan(fov/2) * aspect
    vec4 u_up;         // axe camera, w = tan(fov/2)
    vec4 u_fwd;        // axe camera, w = lacet cumule du ciel
    vec4 u_res;        // largeur, hauteur, pente, accent x
    vec4 u_acc;        // couleur lumineuse du joueur, w = nitro
};
const float PI = 3.14159265;
#define ENV int(u_sky.w + 0.5)

float hash11(float p){ p = fract(p * .1031); p *= p + 33.33; return fract(p * (p + p)); }
float hash21(vec2 p){ vec3 q = fract(vec3(p.xyx) * .1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
vec2 hash22(vec2 p){ vec3 q = fract(vec3(p.xyx) * vec3(.1031,.1030,.0973)); q += dot(q, q.yzx + 33.33); return fract((q.xx + q.yz) * q.zy); }
float noise(vec2 p){
    vec2 i = floor(p), f = fract(p); f = f*f*(3.-2.*f);
    return mix(mix(hash21(i), hash21(i+vec2(1,0)), f.x), mix(hash21(i+vec2(0,1)), hash21(i+vec2(1,1)), f.x), f.y);
}
float fbm(vec2 p){ float a=.5, s=0.; for(int i=0;i<4;i++){ s+=a*noise(p); p=p*2.03+17.1; a*=.5; } return s; }

vec3 skyBase(vec3 d){
    // Ciel basse frequence, partage par le fond, les reflets et le brouillard
    float h = d.y;
    vec3 c;
    if(ENV==0)      c = mix(vec3(.10,.045,.22), vec3(.006,.010,.030), smoothstep(-.02,.45,h)) + vec3(.02,.14,.22)*exp(-max(h,0.)*9.);
    else if(ENV==1) c = mix(vec3(.95,.30,.13), vec3(.10,.045,.17), smoothstep(-.02,.36,h)) ;
    else if(ENV==2) c = mix(vec3(.16,.045,.13), vec3(.018,.016,.040), smoothstep(-.02,.42,h)) + vec3(.02,.06,.10)*exp(-max(h,0.)*8.);
    else if(ENV==3) {
        float t = u_suncol.w;                     // 0 aube, .5 jour, 1 crepuscule
        vec3 hz = mix(mix(vec3(1.0,.62,.42), vec3(.62,.78,.95), smoothstep(0.,.35,t)), vec3(.85,.38,.42), smoothstep(.6,1.,t));
        vec3 zn = mix(mix(vec3(.16,.26,.52), vec3(.14,.34,.72), smoothstep(0.,.35,t)), vec3(.08,.09,.26), smoothstep(.6,1.,t));
        c = mix(hz, zn, smoothstep(-.02,.42,h));
    }
    else if(ENV==4) c = mix(vec3(.05,.04,.12), vec3(.01,.012,.03), smoothstep(-.1,.5,h));
    else            c = mix(vec3(.010,.013,.030), vec3(.003,.004,.009), smoothstep(-.1,.5,h));
    if(ENV==1) c += vec3(1.1,.34,.07) * pow(max(dot(d, normalize(u_sun.xyz)),0.), 6.) * .7;
    if(ENV==3) c += u_suncol.rgb * .25 * pow(max(dot(d, normalize(u_sun.xyz)),0.), 8.);
    return c * mix(1., .10, u_sun.w);
}

vec3 applyFog(vec3 c, float dist, vec3 dir){
    float f = 1. - exp(-pow(dist * u_fog.w, 1.45));
    vec3 fc = u_fog.rgb;
    if(ENV==1 || ENV==3) fc = mix(fc, skyBase(normalize(vec3(dir.x, max(dir.y,.0)+.02, dir.z))), .75);
    else fc = mix(fc, skyBase(normalize(vec3(dir.x, .03, dir.z))), .55);
    return mix(c, fc, clamp(f, 0., 1.));
}

// Faisceau des phares du joueur
float headBeam(vec3 p){
    vec3 d = p - vec3(u_head.x, .7, u_head.z);
    if(d.z < 0.) return 0.;
    float ang = length(vec2(d.x, (d.y + .3) * 1.8)) / (d.z + 2.2);
    float cone = exp(-ang*ang*9.) ;
    return cone * (26. / (26. + d.z*d.z*.035)) * smoothstep(0., 3., d.z) * exp(-d.z*.012);
}
// Halos periodiques des lampadaires (les deux bords)
vec3 lampLight(vec3 p, float s){
    if(u_lamp.w <= 0.) return vec3(0.);
    float sp = u_edge.w;
    float dz = (fract(s / sp + .5) - .5) * sp;
    float dx = abs(p.x) - (u_head.w - 1.0);
    float a = exp(-(dz*dz*.010 + dx*dx*.055));
    return u_lamp.rgb * u_lamp.w * a;
}

